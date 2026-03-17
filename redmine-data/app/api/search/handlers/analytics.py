"""Handler endpoint phân tích tìm kiếm"""
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import SearchLog
from app.services.cache import cache

logger = logging.getLogger(__name__)


async def get_search_analytics(db: Session = Depends(get_db)):
    """Lấy phân tích và thống kê về tìm kiếm.
    
    Endpoint này trả về các thống kê tổng quan về hoạt động tìm kiếm:
    - Tổng số tìm kiếm
    - Số lượng tìm kiếm hôm nay
    - Thời gian phản hồi trung bình
    - Các query phổ biến nhất
    - Thống kê cache Redis
    
    Args:
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - total_searches: Tổng số tìm kiếm (int)
            - searches_today: Số lượng tìm kiếm hôm nay (int)
            - avg_response_time_ms: Thời gian phản hồi trung bình tính bằng milliseconds (float)
            - popular_queries: Danh sách 10 query phổ biến nhất (List[Dict]):
                - query: Nội dung query (str)
                - count: Số lần query được tìm kiếm (int)
            - cache: Thống kê cache từ Redis (Dict):
                - connected: Trạng thái kết nối Redis (bool)
                - total_keys: Tổng số keys trong cache (int)
                - rag_responses: Số lượng RAG responses đã cache (int)
                - embeddings: Số lượng embeddings đã cache (int)
                - hits: Số lượt cache hit (int)
                - misses: Số lượt cache miss (int)
                - hit_rate: Tỷ lệ cache hit (float)
    
    Raises:
        HTTPException: HTTP 500 nếu có lỗi trong quá trình lấy thống kê
    
    Note:
        - Popular queries được sắp xếp theo số lần tìm kiếm giảm dần
        - Cache stats được lấy từ Redis cache service
    """
    try:
        # Tổng số tìm kiếm
        total = db.query(func.count(SearchLog.id)).scalar()
        
        # Tìm kiếm hôm nay
        from datetime import datetime
        today = datetime.now().date()
        today_count = db.query(func.count(SearchLog.id))\
            .filter(func.date(SearchLog.created_at) == today)\
            .scalar()
        
        # Thời gian phản hồi trung bình
        avg_time = db.query(func.avg(SearchLog.response_time_ms)).scalar()
        
        # Các query phổ biến nhất
        popular_queries = db.query(
            SearchLog.query,
            func.count(SearchLog.id).label('count')
        ).group_by(SearchLog.query)\
         .order_by(func.count(SearchLog.id).desc())\
         .limit(10)\
         .all()
        
        # Thống kê cache
        cache_stats = cache.get_cache_stats()
        
        return {
            "total_searches": total,
            "searches_today": today_count,
            "avg_response_time_ms": float(avg_time) if avg_time else 0,
            "popular_queries": [
                {"query": q, "count": c}
                for q, c in popular_queries
            ],
            "cache": cache_stats
        }
        
    except Exception as e:
        logger.error(f"Analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

