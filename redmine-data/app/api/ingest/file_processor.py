"""Các hàm xử lý file cho ingestion"""
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import Source, Chunk, Embedding, SourceDocument
from app.services.extractor import extractor
from app.services.chunker import chunker
from app.services.embedder import embedder

logger = logging.getLogger(__name__)


def process_file(
    file_path: str,
    filename: str,
    source_type: str,
    project_key: Optional[str],
    language: Optional[str],
    db: Session
) -> Dict[str, Any]:
    """
    Xử lý một file: trích xuất, chunk, embed và lưu trữ
    
    Args:
        file_path: Đường dẫn đến file
        filename: Tên file gốc
        source_type: Loại source (document, code, etc.)
        project_key: Project key tùy chọn
        language: Mã ngôn ngữ (mặc định: 'en')
        db: Database session
        
    Returns:
        Dict với kết quả xử lý
    """
    try:
        # Trích xuất nội dung
        logger.info(f"Extracting content from {filename}")
        content = extractor.extract(file_path)
        
        if not content:
            raise ValueError(f"Failed to extract content from {filename}")
        
        # Tính toán hash nội dung
        content_hash = hashlib.sha1(content.encode()).hexdigest()
        
        # Kiểm tra xem source đã tồn tại chưa
        source = db.query(Source).filter(
            Source.source_type == source_type,
            Source.sha1_content == content_hash
        ).first()
        
        if source:
            logger.info(f"Source already exists: {source.id}")
            chunks_count = db.query(Chunk).filter(Chunk.source_id == source.id).count()
            return {
                "source_id": str(source.id),
                "chunks_count": chunks_count,
                "message": "Source already exists"
            }
        
        # Tạo source
        source = Source(
            source_type=source_type,
            external_id=f"manual_{hashlib.sha1((filename + str(datetime.now())).encode()).hexdigest()[:16]}",
            external_url=None,
            project_key=project_key,
            language=language or 'en',
            sha1_content=content_hash,
            sync_status='success',
            last_sync_at=datetime.now()
        )
        db.add(source)
        db.flush()
        
        # Tạo metadata source document
        source_doc = SourceDocument(
            source_id=source.id,
            filename=filename,
            file_path=str(file_path),
            file_size=Path(file_path).stat().st_size if Path(file_path).exists() else None
        )
        db.add(source_doc)
        db.flush()
        
        # Chunk nội dung
        logger.info(f"Chunking content from {filename}")
        chunks_data = chunker.chunk(content, metadata={'filename': filename}, chunk_type=source_type)
        
        if not chunks_data:
            raise ValueError(f"No chunks created from {filename}")
        
        # Tạo embeddings
        logger.info(f"Generating embeddings for {len(chunks_data)} chunks")
        texts = [c['text_content'] for c in chunks_data]
        embeddings = embedder.embed_batch(texts)
        
        # Lưu chunks và embeddings
        successful_chunks = 0
        for chunk_data, embedding_vec in zip(chunks_data, embeddings):
            if len(embedding_vec) != embedder.embedding_dim:
                logger.error(f"Embedding dimension mismatch for chunk, skipping")
                continue
            
            chunk = Chunk(
                source_id=source.id,
                status="pending",
                **chunk_data
            )
            db.add(chunk)
            db.flush()
            
            try:
                quality_score = embedder.compute_quality_score(embedding_vec)
                embedding = Embedding(
                    chunk_id=chunk.id,
                    embedding=embedding_vec,
                    model_name=embedder.model_name,
                    quality_score=quality_score,
                    status="active"
                )
                db.add(embedding)
                chunk.status = "processed"
                successful_chunks += 1
            except Exception as e:
                logger.error(f"Failed to create embedding: {e}")
                chunk.status = "failed"
        
        db.commit()
        logger.info(f"Processed {filename}: {successful_chunks} chunks created")
        
        return {
            "source_id": str(source.id),
            "chunks_count": successful_chunks,
            "message": "File processed successfully"
        }
        
    except Exception as e:
        logger.error(f"File processing failed: {e}", exc_info=True)
        db.rollback()
        raise


async def process_file_async(
    file_path: str,
    filename: str,
    source_type: str,
    project_key: Optional[str],
    language: Optional[str],
    job_id: str,
    db: Session
):
    """Phiên bản async của process_file cho xử lý background jobs.
    
    Hàm này tạo một database session mới cho background task và gọi
    process_file() để xử lý file. Session được đóng tự động sau khi
    xử lý xong, bất kể thành công hay thất bại.
    
    Args:
        file_path: Đường dẫn đến file cần xử lý (string)
        filename: Tên file gốc (string)
        source_type: Loại source (document, code, etc.) (string)
        project_key: Project key tùy chọn (string | None)
        language: Mã ngôn ngữ (string | None)
        job_id: ID của background job (string)
        db: Database session từ main request (không được sử dụng, chỉ để signature)
    
    Note:
        - Tạo session mới (bg_db) để tránh conflict với main request session
        - Session được đóng trong finally block
        - Lỗi được log nhưng không raise (background task)
        - Kết quả được log để tracking
    """
    from app.database import SessionLocal
    
    # Tạo session mới cho background task
    bg_db = SessionLocal()
    try:
        result = process_file(file_path, filename, source_type, project_key, language, bg_db)
        logger.info(f"Background processing completed for {filename}: {result}")
    except Exception as e:
        logger.error(f"Background processing failed for {filename}: {e}", exc_info=True)
    finally:
        bg_db.close()

