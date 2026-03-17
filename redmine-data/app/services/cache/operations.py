"""Các thao tác cache cho RAG responses và embeddings.

Module này cung cấp CacheOperations class để xử lý các thao tác cache:
- RAG response caching: Cache và retrieve RAG responses với TTL
- Embedding caching: Cache và retrieve embeddings với TTL dài hơn
- Cache key generation: Tạo cache keys từ queries/texts với normalization và hashing

Sử dụng Redis để lưu trữ cache với JSON serialization.
"""
import logging
import json
import hashlib
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CacheOperations:
    """Xử lý các thao tác get/set cache cho RAG responses và embeddings.
    
    Class này cung cấp các phương thức để cache và retrieve:
    - RAG responses: Cache các câu trả lời từ RAG chain
    - Embeddings: Cache các embedding vectors
    
    Attributes:
        connection: RedisConnection instance để truy cập Redis client
    """
    
    def __init__(self, connection):
        """Khởi tạo CacheOperations.
        
        Args:
            connection: RedisConnection instance
        """
        self.connection = connection
    
    def _generate_cache_key(self, prefix: str, query: str) -> str:
        """Tạo cache key từ query với format chuẩn.
        
        Hàm này normalize query (lowercase, strip) và tạo hash để tạo
        cache key nhất quán. Format: "rag:{prefix}:{hash}"
        
        Args:
            prefix: Prefix cho cache key (vd: "response", "embedding")
            query: Query string cần tạo key
        
        Returns:
            str: Cache key dạng "rag:{prefix}:{hash}" với hash là 16 ký tự đầu của SHA256
        
        Example:
            >>> _generate_cache_key("response", "Hello World")
            'rag:response:a1b2c3d4e5f6g7h8'
        """
        # Chuẩn hóa query (lowercase, bỏ khoảng trắng)
        normalized_query = query.lower().strip()
        
        # Tạo hash từ query
        cache_hash = hashlib.sha256(normalized_query.encode()).hexdigest()[:16]
        
        return f"rag:{prefix}:{cache_hash}"
    
    def get_rag_response(
        self,
        query: str
    ) -> Optional[Dict[str, Any]]:
        """Lấy RAG response đã cache từ Redis.
        
        Hàm này query Redis để tìm cached response cho query. Query được normalize
        và hash để tạo cache key nhất quán.
        
        Args:
            query: Query string của người dùng (string)
        
        Returns:
            Dict[str, Any] | None: Dictionary chứa RAG response nếu tìm thấy:
                - answer: Câu trả lời (str)
                - sources: Danh sách sources (List[Dict])
                - retrieved_chunks: Danh sách chunks (List[Dict])
                - cached: True (bool)
                - usage: Thông tin usage (Dict, optional)
            None nếu không tìm thấy hoặc Redis không kết nối
        
        Note:
            - Query được normalize (lowercase, strip) trước khi tạo cache key
            - Log cache HIT/MISS để monitoring
            - Trả về None nếu Redis không kết nối hoặc có lỗi
        """
        if not self.connection.is_connected():
            return None
        
        try:
            cache_key = self._generate_cache_key("response", query)
            cached_data = self.connection.client.get(cache_key)
            
            if cached_data:
                logger.debug(f"Cache HIT for query: {query[:50]}...")
                return json.loads(cached_data)
            else:
                logger.debug(f"Cache MISS for query: {query[:50]}...")
                return None
                
        except Exception as e:
            logger.warning(f"Failed to get from cache: {e}")
            return None
    
    def set_rag_response(
        self,
        query: str,
        response: Dict[str, Any],
        ttl_seconds: int = 86400  # Mặc định 1 ngày
    ) -> bool:
        """Cache RAG response vào Redis với TTL.
        
        Hàm này serialize response thành JSON và lưu vào Redis với TTL.
        Query được normalize và hash để tạo cache key nhất quán.
        
        Args:
            query: Query string của người dùng (string)
            response: Dictionary chứa RAG response cần cache (Dict):
                - answer: Câu trả lời (str)
                - sources: Danh sách sources (List[Dict])
                - retrieved_chunks: Danh sách chunks (List[Dict])
                - cached: False (bool)
                - usage: Thông tin usage (Dict, optional)
            ttl_seconds: Thời gian sống của cache tính bằng giây (int, default: 86400 = 1 ngày)
        
        Returns:
            bool: True nếu cache thành công, False nếu thất bại hoặc Redis không kết nối
        
        Note:
            - Response được serialize thành JSON với ensure_ascii=False (hỗ trợ Unicode)
            - Sử dụng Redis SETEX để set với TTL
            - Log debug message khi cache thành công
            - Trả về False nếu Redis không kết nối hoặc có lỗi
        """
        if not self.connection.is_connected():
            return False
        
        try:
            cache_key = self._generate_cache_key("response", query)
            cache_data = json.dumps(response, ensure_ascii=False)
            
            self.connection.client.setex(
                cache_key,
                ttl_seconds,
                cache_data
            )
            
            logger.debug(f"Cached response for query: {query[:50]}... (TTL: {ttl_seconds}s)")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")
            return False
    
    def cache_embedding(
        self,
        text: str,
        embedding: list,
        ttl_seconds: int = 86400 * 7  # 7 ngày cho embeddings
    ) -> bool:
        """Cache text embedding vào Redis với TTL dài hơn.
        
        Hàm này cache embedding vector cho text để tránh tính toán lại.
        Embeddings được cache với TTL dài hơn (7 ngày) vì ít thay đổi hơn so với responses.
        
        Args:
            text: Văn bản đã được embed (string)
            embedding: Embedding vector (List[float]). Thường là list 1024 floats
            ttl_seconds: Thời gian sống của cache tính bằng giây (int, default: 604800 = 7 ngày)
        
        Returns:
            bool: True nếu cache thành công, False nếu thất bại hoặc Redis không kết nối
        
        Note:
            - Text được normalize (lowercase, strip) trước khi tạo cache key
            - Cache key format: "rag:embedding:{hash}"
            - Embedding được serialize cùng với normalized text trong JSON
            - TTL mặc định là 7 ngày (dài hơn responses vì embeddings ít thay đổi)
            - Trả về False nếu Redis không kết nối hoặc có lỗi
        """
        if not self.connection.is_connected():
            return False
        
        try:
            # Chuẩn hóa văn bản cho cache key
            normalized_text = text.lower().strip()
            text_hash = hashlib.sha256(normalized_text.encode()).hexdigest()[:16]
            cache_key = f"rag:embedding:{text_hash}"
            
            cache_data = json.dumps({
                'text': normalized_text,
                'embedding': embedding
            })
            
            self.connection.client.setex(cache_key, ttl_seconds, cache_data)
            return True
            
        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")
            return False
    
    def get_embedding(self, text: str) -> Optional[list]:
        """Lấy embedding đã cache từ Redis.
        
        Hàm này query Redis để tìm cached embedding cho text. Text được normalize
        và hash để tạo cache key nhất quán với cache_embedding().
        
        Args:
            text: Văn bản cần lấy embedding (string)
        
        Returns:
            List[float] | None: Embedding vector nếu tìm thấy trong cache,
                None nếu không tìm thấy hoặc Redis không kết nối
        
        Note:
            - Text được normalize (lowercase, strip) trước khi tìm kiếm
            - Cache key format: "rag:embedding:{hash}"
            - Trả về chỉ embedding vector, không bao gồm text
            - Trả về None nếu Redis không kết nối hoặc có lỗi
        """
        if not self.connection.is_connected():
            return None
        
        try:
            normalized_text = text.lower().strip()
            text_hash = hashlib.sha256(normalized_text.encode()).hexdigest()[:16]
            cache_key = f"rag:embedding:{text_hash}"
            
            cached_data = self.connection.client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return data.get('embedding')
            return None
            
        except Exception as e:
            logger.warning(f"Failed to get cached embedding: {e}")
            return None

