"""Quản lý kết nối Redis.

Module này cung cấp RedisConnection class để quản lý kết nối đến Redis server:
- Connection management: Tự động kết nối và reconnect
- Health checks: Ping định kỳ để đảm bảo connection còn hoạt động
- Error handling: Graceful degradation nếu Redis không khả dụng
- Configuration: Sử dụng settings từ config để kết nối

Sử dụng redis-py library với các options tối ưu cho production.
"""
import logging
import redis
from redis.exceptions import ConnectionError, TimeoutError
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class RedisConnection:
    """Quản lý kết nối Redis với auto-reconnect và error handling.
    
    Class này xử lý việc kết nối đến Redis server, với các tính năng:
    - Auto-reconnect với retry
    - Health check định kỳ
    - Graceful degradation nếu Redis không khả dụng
    
    Attributes:
        redis_url: URL kết nối Redis (string)
        client: Redis client instance (có thể None nếu không kết nối được)
    """
    
    def __init__(self):
        """Khởi tạo RedisConnection và thử kết nối đến Redis.
        
        Note:
            - Nếu kết nối thất bại, client sẽ là None và cache sẽ bị disable
            - Không raise exception nếu kết nối thất bại (graceful degradation)
        """
        self.redis_url = settings.redis_url
        self.client: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self):
        """Kết nối đến Redis server với các cấu hình tối ưu.
        
        Quy trình:
        1. Tạo Redis client từ URL với các options:
           - decode_responses=True: Tự động decode responses thành string
           - socket_connect_timeout=5: Timeout 5 giây khi connect
           - socket_timeout=5: Timeout 5 giây cho operations
           - retry_on_timeout=True: Tự động retry khi timeout
           - health_check_interval=30: Health check mỗi 30 giây
        2. Ping để kiểm tra kết nối
        3. Nếu thất bại, set client = None và log warning
        
        Note:
            - Không raise exception nếu kết nối thất bại
            - Cache sẽ bị disable nếu không kết nối được
        """
        try:
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Kiểm tra kết nối
            self.client.ping()
            logger.info("Redis cache connected successfully")
        except (ConnectionError, TimeoutError, Exception) as e:
            logger.warning(f"Redis connection failed: {e}. Cache will be disabled.")
            self.client = None
    
    def is_connected(self) -> bool:
        """Kiểm tra Redis đã kết nối và hoạt động chưa.
        
        Hàm này kiểm tra cả client object và thực hiện ping để đảm bảo
        kết nối vẫn còn hoạt động.
        
        Returns:
            bool: True nếu client tồn tại và ping thành công, False nếu không
        
        Note:
            - Kiểm tra cả client object (không None) và ping response
            - Nếu ping thất bại, trả về False (có thể do connection lost)
        """
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except:
            return False

