"""Handler tạo embedding cho các chunks.

Job này lấy các chunks chưa có embedding (hoặc embedding không active) và
gắn embedding mới. Việc chunking được thực hiện bởi các job sync (như
redmine_sync), còn job này chỉ tập trung vào bước embedding để tách biệt
chi phí model khỏi bước sync dữ liệu.
"""
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import Chunk, Embedding, ScheduledJob, Source
from app.services.embedder import embedder
if TYPE_CHECKING:
    # Tránh circular import ở runtime
    from app.services.job_executor.executor import JobCancelledException, JobExecutor

logger = logging.getLogger(__name__)


def _chunk_batches(items: List[Chunk], batch_size: int) -> List[List[Chunk]]:
    """Yield danh sách chunks theo batch size."""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def execute_chunk_embedding(
    job: ScheduledJob, db: Session, execution_id: Optional[UUID] = None
) -> Dict[str, Any]:
    """Tạo embeddings cho các chunks chưa có embedding.
    
    Config hỗ trợ:
        - limit: số chunks tối đa mỗi lần chạy (mặc định 200, 0 = không giới hạn)
        - batch_size: số lượng text embedding mỗi batch (mặc định 32)
        - source_type: filter theo Source.source_type (tùy chọn)
        - project_key: filter theo Source.project_key (tùy chọn)
        - include_failed: re-embed nếu embedding status != active (mặc định True)
        - only_pending: chỉ lấy chunk status pending/failed (mặc định True)
    """
    # Import lazily để tránh circular import lúc load module
    from app.services.job_executor.executor import JobCancelledException, JobExecutor

    config = job.config or {}
    limit_config = config.get("limit")
    limit = int(limit_config) if limit_config is not None else 200
    batch_size = int(config.get("batch_size") or 32)
    batch_size = max(batch_size, 1)
    source_type = config.get("source_type")
    project_key = config.get("project_key")
    # Chuẩn hoá boolean (có thể được lưu dạng string trong config)
    include_failed_raw = config.get("include_failed", True)
    only_pending_raw = config.get("only_pending", True)
    if isinstance(include_failed_raw, bool):
        include_failed = include_failed_raw
    else:
        include_failed = str(include_failed_raw).lower() == "true"
    if isinstance(only_pending_raw, bool):
        only_pending = only_pending_raw
    else:
        only_pending = str(only_pending_raw).lower() == "true"

    result: Dict[str, Any] = {
        "selected": 0,
        "processed": 0,
        "failed": 0,
        "errors": [],
    }

    query = db.query(Chunk).outerjoin(Embedding, Embedding.chunk_id == Chunk.id)

    # only_pending=True: chỉ lấy các chunk đang ở trạng thái pending/failed
    if only_pending:
        query = query.filter(Chunk.status.in_(["pending", "failed"]))

    embedding_condition = Embedding.id == None  # noqa: E711
    if include_failed:
        embedding_condition = or_(Embedding.id == None, Embedding.status != "active")  # noqa: E711
    query = query.filter(embedding_condition)

    if source_type or project_key:
        query = query.join(Source, Chunk.source_id == Source.id)
        if source_type:
            query = query.filter(Source.source_type == source_type)
        if project_key:
            query = query.filter(Source.project_key == project_key)

    query = query.order_by(Chunk.created_at.asc())
    if limit > 0:
        query = query.limit(limit)

    chunks = query.all()
    result["selected"] = len(chunks)

    if not chunks:
        logger.info("No chunks to embed for this run")
        return result

    logger.info(f"Embedding job picked {len(chunks)} chunks (limit={limit}, batch_size={batch_size})")

    for chunk_batch in _chunk_batches(chunks, batch_size):
        if execution_id and JobExecutor.is_execution_cancelled(execution_id, db):
            raise JobCancelledException("Job execution was cancelled during embedding")

        texts = [chunk.text_content or "" for chunk in chunk_batch]
        embeddings = embedder.embed_batch(texts, batch_size=batch_size)

        for chunk_obj, embedding_vec in zip(chunk_batch, embeddings):
            try:
                if len(embedding_vec) != embedder.embedding_dim:
                    result["failed"] += 1
                    chunk_obj.status = "failed"
                    result["errors"].append(
                        f"Chunk {chunk_obj.id}: embedding dim {len(embedding_vec)} != {embedder.embedding_dim}"
                    )
                    continue

                existing_embedding = db.query(Embedding).filter(Embedding.chunk_id == chunk_obj.id).first()
                if existing_embedding:
                    db.delete(existing_embedding)
                    db.flush()

                quality_score = embedder.compute_quality_score(embedding_vec)
                embedding = Embedding(
                    chunk_id=chunk_obj.id,
                    embedding=embedding_vec,
                    model_name=embedder.model_name,
                    quality_score=quality_score,
                    status="active",
                )
                db.add(embedding)

                chunk_obj.status = "processed"
                result["processed"] += 1
            except Exception as e:
                logger.error(f"Failed to embed chunk {chunk_obj.id}: {e}", exc_info=True)
                chunk_obj.status = "failed"
                result["failed"] += 1
                result["errors"].append(f"Chunk {chunk_obj.id}: {str(e)}")

        db.commit()

    return result

