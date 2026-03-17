"""Handler endpoint tìm kiếm vector"""
import time
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.services.retriever import retriever
from app.models import SearchLog
from app.api.search.schemas import SearchRequest

logger = logging.getLogger(__name__)


async def vector_search(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """Tìm kiếm vector ngữ nghĩa trả về các chunks liên quan.
    
    Endpoint này thực hiện vector similarity search để tìm các chunks
    liên quan đến query. Khác với RAG search, endpoint này chỉ trả về
    các chunks mà không tạo câu trả lời AI.
    
    Quy trình:
    1. Tạo embedding từ query
    2. Tìm kiếm các chunks tương tự bằng vector similarity
    3. Ghi log tìm kiếm vào search_log
    4. Trả về danh sách chunks với metadata
    
    Args:
        request: SearchRequest chứa query và top_k
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - query: Query đã tìm kiếm (str)
            - results: Danh sách chunks liên quan (List[Dict])
            - count: Số lượng kết quả (int)
            - response_time_ms: Thời gian xử lý tính bằng milliseconds (int)
    
    Raises:
        HTTPException: HTTP 500 nếu có lỗi trong quá trình tìm kiếm
    
    Note:
        - Logging được thực hiện trong session riêng để tránh transaction issues
        - Kết quả được sắp xếp theo similarity score giảm dần
        - Mỗi chunk chứa text, metadata, và similarity_score
    """
    start_time = time.time()
    try:
        # Parse project IDs từ string
        project_ids = None
        if request.list_project_ids:
            try:
                project_ids = [int(pid.strip()) for pid in request.list_project_ids.split(',') if pid.strip()]
                if not project_ids:  # Nếu list rỗng sau khi parse, set về None
                    project_ids = None
                else:
                    logger.info(f"Vector search filtered by project IDs: {project_ids}")
            except ValueError as e:
                logger.warning(f"Invalid project IDs format: {request.list_project_ids}, ignoring filter")
                project_ids = None
        
        # Thực hiện tìm kiếm
        results = retriever.search(
            query=request.query,
            db=db,
            top_k=request.top_k,
            project_ids=project_ids
        )
        
        response_time = int((time.time() - start_time) * 1000)
        
        # Ghi log tìm kiếm (trong session riêng để tránh vấn đề transaction)
        try:
            log_db = SessionLocal()
            try:
                chunk_ids = [r['chunk_id'] for r in results]
                search_log = SearchLog(
                    query=request.query,
                    user_id=request.user_id,
                    filters=None,
                    top_chunk_ids=chunk_ids,
                    response_time_ms=response_time
                )
                log_db.add(search_log)
                log_db.commit()
            except Exception as log_error:
                log_db.rollback()
                logger.warning(f"Failed to log search: {log_error}")
            finally:
                log_db.close()
        except Exception as log_error:
            logger.warning(f"Failed to create log session: {log_error}")
        
        return {
            "query": request.query,
            "results": results,
            "count": len(results),
            "response_time_ms": response_time
        }
        
    except Exception as e:
        # Rollback bất kỳ transaction thất bại nào
        try:
            db.rollback()
        except:
            pass
        
        logger.error(f"Vector search failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

