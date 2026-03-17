"""Service Redis cache chính.

Module này cung cấp RedisCache class - service chính để cache và retrieve:
- RAG responses: Cache các câu trả lời từ RAG chain với TTL 1 ngày
- Embeddings: Cache các embedding vectors với TTL 7 ngày
- Statistics: Lấy thống kê về cache usage và performance

Sử dụng Redis để lưu trữ cache với JSON serialization.
Export singleton instance 'cache' để sử dụng trong toàn bộ ứng dụng.
"""
from app.services.cache.connection import RedisConnection
from app.services.cache.operations import CacheOperations
from app.services.cache.stats import CacheStats


class RedisCache:
    """Service Redis cache chính cho RAG responses và embeddings.
    
    Class này cung cấp interface đơn giản để cache và retrieve:
    - RAG responses: Cache các câu trả lời từ RAG chain
    - Embeddings: Cache các embedding vectors để tăng tốc độ
    
    Attributes:
        connection: RedisConnection instance quản lý kết nối Redis
        operations: CacheOperations instance xử lý các thao tác cache
        stats: CacheStats instance cung cấp thống kê cache
    """
    
    def __init__(self):
        """Khởi tạo RedisCache với các components cần thiết."""
        self.connection = RedisConnection()
        self.operations = CacheOperations(self.connection)
        self.stats = CacheStats(self.connection)
    
    def _is_connected(self) -> bool:
        """Kiểm tra Redis đã kết nối và hoạt động chưa.
        
        Returns:
            bool: True nếu Redis đã kết nối và có thể ping được, False nếu không
        """
        return self.connection.is_connected()
    
    def get_rag_response(self, query: str):
        """Lấy RAG response đã được cache từ Redis.
        
        Args:
            query: Câu hỏi của người dùng (string)
        
        Returns:
            dict | None: Dictionary chứa RAG response nếu tìm thấy trong cache,
                None nếu không tìm thấy hoặc Redis không kết nối
        
        Note:
            - Cache key được tạo từ hash của query (normalized)
            - Trả về None nếu Redis không kết nối
        """
        return self.operations.get_rag_response(query)
    
    def set_rag_response(self, query: str, response: dict, ttl_seconds: int = 86400) -> bool:
        """Cache RAG response vào Redis với TTL.
        
        Args:
            query: Câu hỏi của người dùng (string)
            response: Dictionary chứa RAG response cần cache
            ttl_seconds: Thời gian sống của cache tính bằng giây (mặc định: 86400 = 1 ngày)
        
        Returns:
            bool: True nếu cache thành công, False nếu thất bại hoặc Redis không kết nối
        
        Note:
            - Response được serialize thành JSON trước khi lưu
            - TTL mặc định là 1 ngày (86400 giây)
        """
        return self.operations.set_rag_response(query, response, ttl_seconds)
    
    def cache_embedding(self, text: str, embedding: list, ttl_seconds: int = 86400 * 7) -> bool:
        """Cache text embedding vào Redis với TTL dài hơn.
        
        Args:
            text: Văn bản đã được embed (string)
            embedding: Embedding vector (list of floats)
            ttl_seconds: Thời gian sống của cache tính bằng giây (mặc định: 604800 = 7 ngày)
        
        Returns:
            bool: True nếu cache thành công, False nếu thất bại hoặc Redis không kết nối
        
        Note:
            - Embeddings được cache với TTL dài hơn (7 ngày) vì ít thay đổi hơn
            - Text được normalize (lowercase, strip) trước khi tạo cache key
        """
        return self.operations.cache_embedding(text, embedding, ttl_seconds)
    
    def get_embedding(self, text: str):
        """Lấy embedding đã được cache từ Redis.
        
        Args:
            text: Văn bản cần lấy embedding (string)
        
        Returns:
            list | None: Embedding vector nếu tìm thấy trong cache,
                None nếu không tìm thấy hoặc Redis không kết nối
        
        Note:
            - Text được normalize trước khi tìm kiếm
            - Cache key được tạo từ hash của normalized text
        """
        return self.operations.get_embedding(text)
    
    def get_cache_stats(self):
        """Lấy thống kê về cache Redis.
        
        Returns:
            dict: Dictionary chứa thống kê:
                - connected: Redis có kết nối không (bool)
                - total_keys: Tổng số keys cache (int)
                - rag_responses: Số lượng RAG responses đã cache (int)
                - embeddings: Số lượng embeddings đã cache (int)
                - hits: Số lần cache hit (int)
                - misses: Số lần cache miss (int)
                - hit_rate: Tỷ lệ hit rate tính bằng phần trăm (float)
        
        Note:
            - Trả về stats cơ bản nếu Redis không kết nối
            - Hit rate được tính từ keyspace_hits và keyspace_misses
        """
        return self.stats.get_cache_stats()


# Singleton instance
cache = RedisCache()

