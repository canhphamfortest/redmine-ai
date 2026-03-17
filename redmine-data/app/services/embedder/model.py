"""Quản lý embedding model"""
import logging
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Quản lý việc tải và sử dụng embedding model từ sentence-transformers.
    
    Class này xử lý việc load embedding model từ HuggingFace hoặc local,
    và cung cấp thông tin về kích thước embedding. Model được load một lần
    khi khởi tạo và được sử dụng lại trong suốt vòng đời ứng dụng.
    
    Attributes:
        model_name: Tên model đang sử dụng (str)
        model: SentenceTransformer model instance
        embedding_dim: Kích thước của embedding vectors (int)
    """
    
    def __init__(self, model_name: str = None):
        """Khởi tạo và load embedding model.
        
        Args:
            model_name: Tên model để load (tùy chọn).
                Nếu None, sẽ sử dụng settings.embedding_model.
                Có thể là tên model từ HuggingFace (vd: "sentence-transformers/all-MiniLM-L6-v2")
                hoặc đường dẫn đến model local.
        
        Raises:
            Exception: Nếu không thể load model (network error, file not found, etc.)
        
        Note:
            - Model được download từ HuggingFace nếu chưa có local
            - Quá trình load có thể mất vài phút lần đầu tiên
        """
        self.model_name = model_name or settings.embedding_model
        logger.info(f"Loading embedding model: {self.model_name}")
        
        try:
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Embedding dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

