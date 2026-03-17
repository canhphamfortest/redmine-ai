"""Handler endpoint tạo text bằng AI (không có retrieval)"""
import time
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.services.rag_chain import rag_chain
from app.models import SearchLog
from app.api.search.schemas import GenerateRequest

logger = logging.getLogger(__name__)


async def generate_text(
    request: GenerateRequest,
    db: Session = Depends(get_db)
):
    """Generate text bằng AI trực tiếp (không có vector search và reranking).
    
    Endpoint này thực hiện AI text generation đơn giản:
    1. Gọi AI trực tiếp với prompt đã có (skip_retrieval=True)
    2. Không có vector search, embedding, hay reranking
    3. Cache response trong Redis (1 ngày)
    4. Log usage để tracking
    
    Args:
        request: GenerateRequest chứa prompt
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - prompt: Prompt đã gửi (str)
            - answer: Câu trả lời được tạo bởi AI (str)
            - sources: Danh sách sources (List[Dict], luôn rỗng vì không có retrieval)
            - retrieved_chunks: Danh sách chunks (List[Dict], luôn rỗng vì không có retrieval)
            - cached: True nếu response từ cache, False nếu không (bool)
            - response_time_ms: Thời gian xử lý tính bằng milliseconds (int)
    
    Raises:
        HTTPException: HTTP 500 nếu có lỗi trong quá trình generate
    
    Note:
        - Responses được cache trong Redis với TTL 1 ngày
        - Search log được ghi trong session riêng để không block response
        - Logging được thực hiện non-blocking để không ảnh hưởng performance
        - Không có retrieval nên retrieved_chunks và sources luôn là empty arrays
    """
    start_time = time.time()
    try:
        result = rag_chain.generate_answer(
            query=request.prompt,
            db=db,
            use_cache=True,
            skip_retrieval=True  # Bỏ qua retrieval, chỉ gọi AI trực tiếp
        )
        
        response_time = int((time.time() - start_time) * 1000)
        
        # Chuẩn bị response trước (log không nên ảnh hưởng đến response)
        response = {
            "prompt": request.prompt,
            "answer": result['answer'],
            "sources": result.get('sources', []),  # Luôn rỗng vì không có retrieval
            "retrieved_chunks": result.get('retrieved_chunks', []),  # Luôn rỗng vì không có retrieval
            "cached": result.get('cached', False),
            "response_time_ms": response_time
        }
        
        # Ghi log tìm kiếm vào search_log SAU KHI chuẩn bị response (non-blocking, trong session riêng)
        # Chỉ để ghi log và không nên ảnh hưởng đến API call hoặc response
        try:
            log_db = SessionLocal()
            try:
                # Không có chunks vì không có retrieval
                search_log = SearchLog(
                    query=request.prompt,
                    user_id=request.user_id,
                    filters=None,
                    top_chunk_ids=[],
                    response_time_ms=response_time
                )
                log_db.add(search_log)
                log_db.commit()
            except Exception as log_error:
                log_db.rollback()
                logger.warning(f"Failed to log generate_text search (non-blocking): {log_error}")
            finally:
                log_db.close()
        except Exception as log_error:
            logger.warning(f"Failed to create log session for generate_text (non-blocking): {log_error}")
        
        return response
        
    except Exception as e:
        logger.error(f"Generate text failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

