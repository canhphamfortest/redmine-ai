"""Service embedding chính.

Module này cung cấp EmbeddingService - service chính để tạo embeddings từ text.
Sử dụng sentence-transformers để tạo embeddings chất lượng cao cho vector search.

Các thành phần:
- EmbeddingService: Class chính cung cấp interface để tạo embeddings
- EmbeddingModel: Quản lý model loading và embedding dimension
- EmbeddingGenerator: Xử lý việc tạo embeddings với caching
- QualityScorer: Tính điểm chất lượng của embeddings

Module export singleton instance 'embedder' để sử dụng trong toàn bộ ứng dụng.
"""
from app.services.embedder.model import EmbeddingModel
from app.services.embedder.generation import EmbeddingGenerator
from app.services.embedder.quality import QualityScorer


class EmbeddingService:
    """Service chính để tạo embeddings bằng sentence-transformers.
    
    Class này cung cấp interface đơn giản để tạo embeddings từ văn bản,
    với hỗ trợ caching và tính toán quality score. Sử dụng sentence-transformers
    library để tạo embeddings chất lượng cao.
    
    Attributes:
        model: EmbeddingModel instance quản lý model loading
        generator: EmbeddingGenerator instance xử lý việc tạo embeddings
        quality_scorer: QualityScorer instance tính điểm chất lượng
        embedding_dim: Kích thước của embedding vectors (int)
    """
    
    def __init__(self, model_name: str = None):
        """Khởi tạo EmbeddingService.
        
        Args:
            model_name: Tên model embedding để sử dụng (tùy chọn).
                Nếu None, sẽ sử dụng model từ settings.embedding_model
        """
        self.model = EmbeddingModel(model_name)
        self.model_name = self.model.model_name  # Expose model_name for compatibility
        self.generator = EmbeddingGenerator(self.model)
        self.quality_scorer = QualityScorer(self.model.embedding_dim)
        self.embedding_dim = self.model.embedding_dim
    
    def embed_text(self, text: str, use_cache: bool = True):
        """Tạo embedding vector cho một văn bản đơn lẻ.
        
        Hàm này tạo embedding cho một văn bản, với tùy chọn sử dụng cache
        để tăng tốc độ cho các văn bản đã được xử lý trước đó.
        
        Args:
            text: Văn bản cần tạo embedding (string)
            use_cache: Có sử dụng cache không (mặc định: True).
                Nếu True, sẽ kiểm tra cache trước và lưu kết quả sau khi tạo
        
        Returns:
            List[float]: Embedding vector dạng list các số float
        
        Note:
            - Văn bản rỗng sẽ trả về vector zero
            - Embeddings được cache trong 7 ngày
        """
        return self.generator.embed_text(text, use_cache)
    
    def embed_batch(self, texts: list, batch_size: int = 32):
        """Tạo embeddings cho nhiều văn bản cùng lúc (batch processing).
        
        Hàm này xử lý nhiều văn bản cùng lúc, hiệu quả hơn việc gọi embed_text
        nhiều lần. Tự động lọc các văn bản rỗng và giữ nguyên thứ tự.
        
        Args:
            texts: Danh sách các văn bản cần tạo embedding (List[str])
            batch_size: Số lượng văn bản xử lý trong mỗi batch (mặc định: 32).
                Batch size lớn hơn sẽ nhanh hơn nhưng tốn nhiều memory hơn
        
        Returns:
            List[List[float]]: Danh sách các embedding vectors, mỗi vector
                tương ứng với một văn bản trong input. Văn bản rỗng sẽ có
                vector zero nhưng vẫn giữ vị trí trong list.
        
        Note:
            - Văn bản rỗng sẽ được thay thế bằng vector zero
            - Progress bar sẽ hiển thị nếu có hơn 100 văn bản
        """
        return self.generator.embed_batch(texts, batch_size)
    
    def compute_quality_score(self, embedding: list) -> float:
        """Tính điểm chất lượng cho một embedding vector.
        
        Điểm chất lượng dựa trên norm (độ lớn) của vector. Embeddings có
        norm quá thấp có thể chứa ít thông tin hơn. Điểm được chuẩn hóa về
        khoảng 0-1.
        
        Args:
            embedding: Embedding vector cần đánh giá (List[float])
        
        Returns:
            float: Điểm chất lượng từ 0.0 đến 1.0, cao hơn là tốt hơn
        
        Note:
            - Trả về 0.5 nếu có lỗi trong quá trình tính toán
        """
        return self.quality_scorer.compute_quality_score(embedding)


# Singleton instance
embedder = EmbeddingService()

