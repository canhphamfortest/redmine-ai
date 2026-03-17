"""Thống kê cache.

Module này cung cấp CacheStats class để thu thập và trả về thống kê về Redis cache:
- Key counts: Đếm tổng số keys và phân loại (responses vs embeddings)
- Hit/miss rates: Lấy statistics từ Redis INFO command
- Connection status: Kiểm tra Redis connection

Sử dụng Redis INFO và KEYS commands để thu thập statistics.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CacheStats:
    """Xử lý thống kê và monitoring cho Redis cache.
    
    Class này cung cấp thông tin về:
    - Số lượng keys đã cache
    - Phân loại keys (responses vs embeddings)
    - Hit/miss rates
    - Connection status
    
    Attributes:
        connection: RedisConnection instance để truy cập Redis client
    """
    
    def __init__(self, connection):
        """Khởi tạo CacheStats.
        
        Args:
            connection: RedisConnection instance
        """
        self.connection = connection
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Lấy thống kê chi tiết về Redis cache.
        
        Hàm này thu thập thông tin từ Redis:
        - Đếm tổng số keys với prefix "rag:*"
        - Phân loại keys (response vs embedding)
        - Lấy hit/miss statistics từ Redis INFO
        - Tính hit rate percentage
        
        Returns:
            Dict[str, Any]: Dictionary chứa thống kê:
                - connected: Redis có kết nối không (bool)
                - total_keys: Tổng số keys cache (int)
                - rag_responses: Số lượng RAG response keys (int)
                - embeddings: Số lượng embedding keys (int)
                - hits: Số lần cache hit từ Redis INFO (int)
                - misses: Số lần cache miss từ Redis INFO (int)
                - hit_rate: Tỷ lệ hit rate tính bằng phần trăm (float)
                - error: Error message nếu có lỗi (string, optional)
        
        Note:
            - Trả về stats cơ bản nếu Redis không kết nối
            - Hit rate = hits / (hits + misses) * 100
            - Sử dụng Redis INFO command để lấy statistics
        """
        if not self.connection.is_connected():
            return {
                'connected': False,
                'total_keys': 0,
                'rag_responses': 0,
                'embeddings': 0
            }
        
        try:
            info = self.connection.client.info('stats')
            all_keys = self.connection.client.keys("rag:*")
            
            response_keys = len([k for k in all_keys if k.startswith("rag:response:")])
            embedding_keys = len([k for k in all_keys if k.startswith("rag:embedding:")])
            
            return {
                'connected': True,
                'total_keys': len(all_keys),
                'rag_responses': response_keys,
                'embeddings': embedding_keys,
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': (
                    info.get('keyspace_hits', 0) / 
                    (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1))
                ) * 100
            }
            
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {'connected': False, 'error': str(e)}

