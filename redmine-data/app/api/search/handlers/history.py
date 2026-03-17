"""Handler endpoint lịch sử tìm kiếm"""
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SearchLog
from app.services.cache import cache

logger = logging.getLogger(__name__)


async def get_search_history(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Lấy lịch sử tìm kiếm gần đây với trạng thái cache.
    
    Endpoint này trả về danh sách các tìm kiếm gần đây nhất, kèm theo
    thông tin về việc response có được cache hay không.
    
    Args:
        limit: Số lượng tìm kiếm gần đây nhất cần trả về (mặc định: 50)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - history: Danh sách lịch sử tìm kiếm (List[Dict]):
                - id: UUID của search log (str)
                - query: Query đã tìm kiếm (str)
                - response_time_ms: Thời gian phản hồi tính bằng milliseconds (int)
                - created_at: Thời gian tìm kiếm (str, ISO format)
                - cached: True nếu response đang được cache, False nếu không (bool)
    
    Raises:
        HTTPException: HTTP 500 nếu có lỗi trong quá trình lấy lịch sử
    
    Note:
        - Lịch sử được sắp xếp theo created_at giảm dần (mới nhất trước)
        - Cache status được kiểm tra bằng cách query Redis cache
        - Nếu cache không kết nối, cached sẽ luôn là False
    """
    try:
        logs = db.query(SearchLog)\
            .order_by(SearchLog.created_at.desc())\
            .limit(limit)\
            .all()
        
        # Kiểm tra trạng thái cache cho mỗi query
        history_with_cache = []
        for log in logs:
            cache_status = cache.get_rag_response(log.query)
            history_with_cache.append({
                "id": str(log.id),
                "query": log.query,
                "response_time_ms": log.response_time_ms,
                "created_at": log.created_at.isoformat(),
                "cached": cache_status is not None
            })
        
        return {
            "history": history_with_cache
        }
        
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

