"""Tạo embedding"""
import logging
from typing import List

from app.services.cache import cache

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Xử lý việc tạo embedding từ văn bản sử dụng embedding model.
    
    Class này cung cấp các phương thức để tạo embeddings từ văn bản đơn lẻ
    hoặc batch, với hỗ trợ caching để tối ưu hiệu suất.
    
    Hỗ trợ tự động thêm prefix cho E5 models (intfloat/multilingual-e5-*):
    - "query: " prefix cho queries (embed_text)
    - "passage: " prefix cho documents (embed_batch)
    
    Attributes:
        model: EmbeddingModel instance chứa SentenceTransformer model
        embedding_dim: Kích thước của embedding vectors (int)
        is_e5_model: Boolean cho biết model có phải E5 model không
    """
    
    def __init__(self, model):
        """Khởi tạo EmbeddingGenerator.
        
        Args:
            model: EmbeddingModel instance đã được load
        """
        self.model = model
        self.embedding_dim = model.embedding_dim
        # Kiểm tra xem model có phải E5 model không (cần prefix)
        self.is_e5_model = self._is_e5_model(model.model_name)
        if self.is_e5_model:
            logger.info(f"E5 model detected: {model.model_name}. Will add appropriate prefixes.")
    
    def _is_e5_model(self, model_name: str) -> bool:
        """Kiểm tra xem model có phải E5 model không (cần prefix).
        
        E5 models (intfloat/multilingual-e5-*, intfloat/e5-*) yêu cầu prefix:
        - "query: " cho queries
        - "passage: " cho documents/passages
        
        Args:
            model_name: Tên model cần kiểm tra
            
        Returns:
            bool: True nếu là E5 model, False nếu không
        """
        if not model_name:
            return False
        model_name_lower = model_name.lower()
        # Kiểm tra các pattern phổ biến của E5 models
        # Pattern: "multilingual-e5", "e5-large", "e5-base", "e5-small", etc.
        # hoặc model từ intfloat organization có "e5" trong tên
        return (
            "multilingual-e5" in model_name_lower or
            ("e5-" in model_name_lower and "intfloat" in model_name_lower) or
            model_name_lower.startswith("intfloat/e5") or
            model_name_lower.startswith("intfloat/multilingual-e5")
        )
    
    def _add_query_prefix(self, text: str) -> str:
        """Thêm prefix "query: " cho E5 models nếu cần.
        
        Args:
            text: Văn bản gốc
            
        Returns:
            str: Văn bản đã thêm prefix nếu là E5 model
        """
        if self.is_e5_model and not text.strip().startswith("query:"):
            return f"query: {text}"
        return text
    
    def _add_passage_prefix(self, text: str) -> str:
        """Thêm prefix "passage: " cho E5 models nếu cần.
        
        Args:
            text: Văn bản gốc
            
        Returns:
            str: Văn bản đã thêm prefix nếu là E5 model
        """
        if self.is_e5_model and not text.strip().startswith("passage:"):
            return f"passage: {text}"
        return text
    
    def embed_text(self, text: str, use_cache: bool = True) -> List[float]:
        """Tạo embedding cho một văn bản đơn lẻ với tùy chọn caching.
        
        Hàm này tạo embedding vector cho một văn bản. Nếu use_cache=True,
        sẽ kiểm tra cache trước khi tạo mới và lưu kết quả vào cache sau đó.
        
        Đối với E5 models, tự động thêm prefix "query: " vì hàm này thường
        được sử dụng cho queries trong vector search.
        
        Args:
            text: Văn bản cần tạo embedding (string)
            use_cache: Có sử dụng cache không (mặc định: True).
                Nếu True, sẽ kiểm tra Redis cache trước và lưu kết quả
        
        Returns:
            List[float]: Embedding vector dạng list các số float.
                Nếu text rỗng, trả về vector zero.
                Nếu có lỗi, trả về vector zero.
        
        Note:
            - Văn bản rỗng hoặc chỉ có whitespace sẽ trả về vector zero
            - Embeddings được cache trong Redis với TTL 7 ngày
            - Cache key dựa trên nội dung text đã có prefix (nếu là E5 model)
            - E5 models: tự động thêm "query: " prefix
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return [0.0] * self.embedding_dim
        
        # Thêm prefix cho E5 models (query prefix cho embed_text)
        prefixed_text = self._add_query_prefix(text)
        
        # Kiểm tra cache trước (cache key dựa trên prefixed text)
        if use_cache:
            cached_embedding = cache.get_embedding(prefixed_text)
            if cached_embedding:
                logger.debug(f"Using cached embedding for text: {text[:50]}...")
                return cached_embedding
        
        try:
            embedding = self.model.model.encode(
                prefixed_text,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            embedding_list = embedding.tolist()
            
            # Cache embedding (TTL 7 ngày) - cache với prefixed text
            if use_cache:
                cache.cache_embedding(prefixed_text, embedding_list, ttl_seconds=86400 * 7)
            
            return embedding_list
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return [0.0] * self.embedding_dim
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Tạo embeddings cho nhiều văn bản cùng lúc (batch processing).
        
        Hàm này xử lý batch văn bản cùng lúc, hiệu quả hơn nhiều so với
        gọi embed_text nhiều lần. Tự động lọc các văn bản rỗng nhưng vẫn
        giữ nguyên thứ tự và vị trí trong kết quả.
        
        Đối với E5 models, tự động thêm prefix "passage: " vì hàm này thường
        được sử dụng cho documents/chunks trong embedding job.
        
        Args:
            texts: Danh sách các văn bản cần tạo embedding (List[str])
            batch_size: Số lượng văn bản xử lý trong mỗi batch (mặc định: 32).
                Batch size lớn hơn sẽ nhanh hơn nhưng tốn nhiều memory hơn.
                Nên điều chỉnh dựa trên GPU/CPU và memory available.
        
        Returns:
            List[List[float]]: Danh sách các embedding vectors, mỗi vector
                tương ứng với một văn bản trong input list. Văn bản rỗng sẽ
                có vector zero nhưng vẫn giữ vị trí trong list.
        
        Note:
            - Văn bản rỗng hoặc chỉ có whitespace sẽ được thay thế bằng vector zero
            - Progress bar sẽ hiển thị nếu có hơn 100 văn bản
            - Nếu có lỗi, tất cả văn bản sẽ có vector zero
            - Batch processing không sử dụng cache (vì phức tạp và ít lợi ích)
            - E5 models: tự động thêm "passage: " prefix cho mỗi text
        """
        if not texts:
            return []
        
        # Lọc các văn bản rỗng và thêm prefix cho E5 models
        valid_texts = []
        for i, t in enumerate(texts):
            if t and t.strip():
                # Thêm prefix "passage: " cho E5 models
                prefixed_text = self._add_passage_prefix(t)
                valid_texts.append((i, prefixed_text))
        
        if not valid_texts:
            logger.warning("All texts are empty")
            return [[0.0] * self.embedding_dim] * len(texts)
        
        try:
            indices, valid_text_list = zip(*valid_texts)
            
            # Tạo embeddings với prefixed texts
            embeddings = self.model.model.encode(
                valid_text_list,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=len(valid_text_list) > 100
            )
            
            # Ánh xạ lại về vị trí ban đầu
            result = [[0.0] * self.embedding_dim] * len(texts)
            for idx, emb in zip(indices, embeddings):
                result[idx] = emb.tolist()
            
            logger.info(f"Generated {len(valid_texts)} embeddings")
            return result
            
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}")
            return [[0.0] * self.embedding_dim] * len(texts)

