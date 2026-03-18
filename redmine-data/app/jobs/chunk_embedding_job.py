"""Job tạo vector embeddings cho các chunks chưa được xử lý."""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.jobs.base_job import BaseJob, JobOption
from app.models import Chunk, Embedding, Source
from app.services.embedder import embedder

logger = logging.getLogger(__name__)


class ChunkEmbeddingJob(BaseJob):
    """Tạo vector embeddings cho các chunks chưa có embedding.

    Job này lấy các chunks ở trạng thái pending/failed và tạo embeddings.
    Việc chunking được thực hiện bởi các job sync (như RedmineSyncJob).
    """

    name = "chunk_embedding"
    label = "Chunk Embedding"
    description = "Tạo vector embeddings cho các chunks chưa được xử lý"

    def options(self) -> List[JobOption]:
        return [
            JobOption(
                key="limit",
                type="number",
                label="Max Chunks per Run",
                default=200,
                help="Số chunks tối đa mỗi lần chạy (0 = không giới hạn)",
            ),
            JobOption(
                key="batch_size",
                type="number",
                label="Embedding Batch Size",
                default=32,
                help="Số lượng texts gửi mỗi batch tới embedding model",
            ),
            JobOption(
                key="source_type",
                type="text",
                label="Source Type Filter",
                default=None,
                help="Chỉ embed chunks thuộc source type này (bỏ trống = tất cả)",
                placeholder="redmine_issue",
            ),
            JobOption(
                key="project_key",
                type="text",
                label="Project Key Filter",
                default=None,
                help="Chỉ embed chunks thuộc project này (bỏ trống = tất cả)",
                placeholder="myproject",
            ),
            JobOption(
                key="include_failed",
                type="checkbox",
                label="Re-embed Failed/Inactive Embeddings",
                default=True,
                help="Tạo lại embedding cho chunks có embedding status != active",
            ),
            JobOption(
                key="only_pending",
                type="checkbox",
                label="Only Pending/Failed Chunks",
                default=True,
                help="Chỉ lấy chunks có status pending hoặc failed",
            ),
        ]

    def execute(self, db: Session, execution_id: Optional[UUID] = None, **kwargs) -> Dict[str, Any]:
        """Tạo embeddings cho các chunks chưa có embedding.

        Args:
            db: Database session
            execution_id: UUID của JobExecution để check cancellation
            **kwargs: Config từ ScheduledJob.config (xem options())

        Returns:
            Dict chứa:
                - selected (int): Số chunks được chọn để embed
                - processed (int): Số chunks đã embed thành công
                - failed (int): Số chunks thất bại
                - errors (List[str]): Danh sách lỗi
        """
        from app.services.job_executor.exceptions import JobCancelledException, check_cancelled

        # Parse config
        limit_raw = kwargs.get("limit")
        limit = int(limit_raw) if limit_raw is not None else 200
        batch_size = max(int(kwargs.get("batch_size") or 32), 1)
        source_type = kwargs.get("source_type")
        project_key = kwargs.get("project_key")

        # Chuẩn hoá boolean (có thể được lưu dạng string trong config)
        def to_bool(val, default):
            if isinstance(val, bool):
                return val
            if val is None:
                return default
            return str(val).lower() == "true"

        include_failed = to_bool(kwargs.get("include_failed"), True)
        only_pending = to_bool(kwargs.get("only_pending"), True)

        result: Dict[str, Any] = {"selected": 0, "processed": 0, "failed": 0, "errors": []}

        # Build base query — no .limit()/.all() here; pagination done per batch below
        base_query = db.query(Chunk).outerjoin(Embedding, Embedding.chunk_id == Chunk.id)

        if only_pending:
            base_query = base_query.filter(Chunk.status.in_(["pending", "failed"]))

        embedding_condition = Embedding.id == None  # noqa: E711
        if include_failed:
            embedding_condition = or_(Embedding.id == None, Embedding.status != "active")  # noqa: E711
        base_query = base_query.filter(embedding_condition)

        if source_type or project_key:
            base_query = base_query.join(Source, Chunk.source_id == Source.id)
            if source_type:
                base_query = base_query.filter(Source.source_type == source_type)
            if project_key:
                base_query = base_query.filter(Source.project_key == project_key)

        base_query = base_query.order_by(Chunk.created_at.asc())

        logger.info(
            f"Embedding job starting (limit={limit}, batch_size={batch_size}, "
            f"source_type={source_type}, project_key={project_key})"
        )

        # ── DB-level pagination: fetch batch_size rows at a time ─────────────
        # This avoids loading all matching chunks into memory at once (OOM risk
        # when limit==0 or the dataset is large).
        #
        # Important: after each batch we commit (which may change chunk.status),
        # so we must NOT use a plain incrementing offset — processed rows would
        # shift the result set and cause skips.  Instead we re-query using a
        # cursor on Chunk.created_at + Chunk.id so already-processed rows are
        # naturally excluded by the status / embedding filters.
        offset = 0
        total_remaining = limit  # 0 means unlimited

        while True:
            check_cancelled(execution_id, db)

            # How many rows to fetch this round?
            fetch_size = batch_size
            if total_remaining > 0:
                fetch_size = min(batch_size, total_remaining)

            chunk_batch = base_query.limit(fetch_size).offset(offset).all()

            if not chunk_batch:
                break  # No more rows matching the filters

            result["selected"] += len(chunk_batch)
            logger.debug(f"Fetched {len(chunk_batch)} chunks at offset {offset}")

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

                    existing = db.query(Embedding).filter(Embedding.chunk_id == chunk_obj.id).first()
                    if existing:
                        db.delete(existing)
                        db.flush()

                    quality_score = embedder.compute_quality_score(embedding_vec)
                    db.add(
                        Embedding(
                            chunk_id=chunk_obj.id,
                            embedding=embedding_vec,
                            model_name=embedder.model_name,
                            quality_score=quality_score,
                            status="active",
                        )
                    )
                    chunk_obj.status = "processed"
                    result["processed"] += 1

                except Exception as e:
                    logger.error(f"Failed to embed chunk {chunk_obj.id}: {e}", exc_info=True)
                    # Rollback first — session may be in error state after a
                    # failed db.flush()/db.add(); without this db.commit() at
                    # the end of the batch raises PendingRollbackError.
                    db.rollback()
                    # Re-apply the status update after rollback (the ORM object
                    # is still in-memory; rollback only reverts unflushed DB ops)
                    chunk_obj.status = "failed"
                    result["failed"] += 1
                    result["errors"].append(f"Chunk {chunk_obj.id}: {str(e)}")

            # Commit after every batch — keeps memory low, progress durable
            db.commit()

            # After commit, successfully processed chunks change status and are
            # excluded from base_query on the next iteration; failed ones stay
            # (status still "failed") and would re-appear at the same offset.
            # Advance offset only by the number of failed chunks to avoid skips.
            batch_failed = sum(1 for c in chunk_batch if c.status == "failed")
            offset += batch_failed

            # Stop if we've hit the overall limit
            if total_remaining > 0:
                total_remaining -= len(chunk_batch)
                if total_remaining <= 0:
                    break

        if result["selected"] == 0:
            logger.info("No chunks to embed for this run")

        return result
