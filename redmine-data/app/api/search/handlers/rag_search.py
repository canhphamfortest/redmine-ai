"""Handler endpoint tìm kiếm RAG"""
import time
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.services.rag_chain import rag_chain
from app.models import SearchLog
from app.api.search.schemas import RAGRequest

logger = logging.getLogger(__name__)


async def rag_search(
    request: RAGRequest,
    db: Session = Depends(get_db)
):
    """RAG search với câu trả lời được tạo bởi AI (có Redis caching).
    
    Endpoint này thực hiện RAG (Retrieval-Augmented Generation) search:
    1. Tìm kiếm các chunks liên quan bằng vector similarity
    2. Tạo câu trả lời AI dựa trên context từ chunks
    3. Trích xuất sources từ chunks
    4. Cache response trong Redis (1 ngày)
    
    Args:
        request: RAGRequest chứa query và top_k
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - query: Query đã tìm kiếm (str)
            - answer: Câu trả lời được tạo bởi AI (str)
            - sources: Danh sách sources được trích xuất (List[Dict])
            - retrieved_chunks: Danh sách chunks đã retrieve (List[Dict])
            - cached: True nếu response từ cache, False nếu không (bool)
            - response_time_ms: Thời gian xử lý tính bằng milliseconds (int)
            - timing_breakdown: Chi tiết thời gian từng phần (Dict, optional)
    
    Raises:
        HTTPException: HTTP 500 nếu có lỗi trong quá trình tìm kiếm hoặc tạo câu trả lời
    
    Note:
        - Responses được cache trong Redis với TTL 1 ngày
        - Search log được ghi trong session riêng để không block response
        - Logging được thực hiện non-blocking để không ảnh hưởng performance
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
                    logger.info(f"RAG search filtered by project IDs: {project_ids}")
            except ValueError as e:
                logger.warning(f"Invalid project IDs format: {request.list_project_ids}, ignoring filter")
                project_ids = None
        
        result = rag_chain.generate_answer(
            query=request.query,
            db=db,
            use_cache=True,
            project_ids=project_ids
        )
        
        response_time = int((time.time() - start_time) * 1000)
        
        # Log timing breakdown nếu có
        timing_breakdown = result.get('timing_breakdown', {})
        if timing_breakdown:
            logger.info(
                f"RAG Search Timing - Query: '{request.query[:50]}...' | "
                f"Total: {response_time}ms | "
                f"Cache: {timing_breakdown.get('cache_check_ms', 0)}ms | "
                f"Embedding: {timing_breakdown.get('embedding_generation_ms', 0)}ms | "
                f"VectorSearch: {timing_breakdown.get('vector_search_ms', 0)}ms | "
                f"ContextBuild: {timing_breakdown.get('context_build_ms', 0)}ms | "
                f"LLM: {timing_breakdown.get('llm_generation_ms', 0)}ms | "
                f"SourceExtract: {timing_breakdown.get('source_extract_ms', 0)}ms | "
                f"CacheWrite: {timing_breakdown.get('cache_write_ms', 0)}ms"
            )
        
        # Chuẩn bị response trước (log không nên ảnh hưởng đến response)
        response = {
            "query": request.query,
            "answer": result['answer'],
            "sources": result['sources'],
            "retrieved_chunks": result['retrieved_chunks'],
            "cached": result.get('cached', False),
            "response_time_ms": response_time
        }
        
        # Thêm timing breakdown vào response nếu có (để debug)
        if result.get('timing_breakdown'):
            response['timing_breakdown'] = result['timing_breakdown']
        
        # Ghi log tìm kiếm vào search_log SAU KHI chuẩn bị response (non-blocking, trong session riêng)
        # Chỉ để ghi log và không nên ảnh hưởng đến API call hoặc response
        try:
            log_db = SessionLocal()
            try:
                chunk_ids = [chunk.get('chunk_id') for chunk in result.get('retrieved_chunks', []) if chunk.get('chunk_id')]
                search_log = SearchLog(
                    query=request.query,
                    user_id=request.user_id,
                    filters=None,
                    top_chunk_ids=chunk_ids,
                    response_time_ms=response_time,
                    usage_log_id=result.get('usage_log_id'),
                    generation_time_ms=result.get('generation_time_ms')
                )
                log_db.add(search_log)
                log_db.commit()
            except Exception as log_error:
                log_db.rollback()
                logger.warning(f"Failed to log RAG search (non-blocking): {log_error}")
            finally:
                log_db.close()
        except Exception as log_error:
            logger.warning(f"Failed to create log session for RAG (non-blocking): {log_error}")
        
        return response
        
    except Exception as e:
        logger.error(f"RAG search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

