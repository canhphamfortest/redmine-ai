"""Handler thống kê ingestion"""
import logging
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import Source, SourceDocument, Chunk, Embedding

logger = logging.getLogger(__name__)


async def get_ingestion_stats(db: Session = Depends(get_db)):
    """Lấy thống kê tổng quan về ingestion.
    
    Endpoint này trả về số lượng tổng thể của các entities trong hệ thống:
    - Tổng số sources
    - Tổng số source documents
    - Tổng số chunks
    - Tổng số embeddings
    
    Args:
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa thống kê:
            - total_sources: Tổng số sources trong database (int)
            - total_source_documents: Tổng số source documents (int)
            - total_chunks: Tổng số chunks trong database (int)
            - total_embeddings: Tổng số embeddings trong database (int)
    
    Note:
        - Sử dụng SQL COUNT để đếm nhanh
        - Không filter, trả về tổng số của tất cả records
    """
    total_sources = db.query(func.count(Source.id)).scalar()
    total_source_documents = db.query(func.count(SourceDocument.id)).scalar()
    total_chunks = db.query(func.count(Chunk.id)).scalar()
    total_embeddings = db.query(func.count(Embedding.id)).scalar()
    
    return {
        "total_sources": total_sources,
        "total_source_documents": total_source_documents,
        "total_chunks": total_chunks,
        "total_embeddings": total_embeddings
    }

