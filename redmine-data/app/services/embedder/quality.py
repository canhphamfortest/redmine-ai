"""Tính điểm chất lượng embedding"""
import logging
from typing import List
import numpy as np

logger = logging.getLogger(__name__)


class QualityScorer:
    """Tính điểm chất lượng cho embedding vectors.
    
    Class này đánh giá chất lượng của embedding dựa trên nhiều yếu tố:
    - Norm (độ lớn) của vector
    - Variance (phương sai) của các giá trị trong vector
    - Magnitude distribution (phân phối độ lớn)
    
    Công thức được cải thiện để phù hợp với nhiều loại embedding models khác nhau,
    bao gồm cả các models normalize về unit vectors (như E5) và các models không normalize.
    
    Attributes:
        embedding_dim: Kích thước của embedding vectors (int)
    """
    
    def __init__(self, embedding_dim: int):
        """Khởi tạo QualityScorer.
        
        Args:
            embedding_dim: Kích thước của embedding vectors
        """
        self.embedding_dim = embedding_dim
    
    def compute_quality_score(self, embedding: List[float]) -> float:
        """Tính điểm chất lượng cho một embedding vector.
        
        Điểm chất lượng được tính dựa trên các metrics hợp lý để đánh giá chất lượng
        của embedding vector. Công thức này phù hợp với cả normalized (E5) và
        non-normalized (mxbai) models.
        
        Metrics được sử dụng:
        
        1. Norm score (50%): Đánh giá độ lớn của vector
           - Normalized models (E5): norm ≈ 1.0 là lý tưởng
           - Non-normalized models: norm hợp lý (không quá nhỏ, không quá lớn)
           - Vector quá nhỏ (norm < 0.1) hoặc quá lớn (norm > 10) → điểm thấp
        
        2. Variance score (30%): Đánh giá độ phân tán của các giá trị
           - Variance hợp lý cho thấy embedding có thông tin đa dạng
           - Variance quá thấp → embedding đơn điệu (có thể là zero vector hoặc constant)
           - Variance quá cao → có thể có outliers hoặc noise
        
        3. Magnitude consistency (20%): Đánh giá tính nhất quán của các giá trị
           - Kiểm tra xem các giá trị có phân bố hợp lý không
           - Sử dụng coefficient of variation (CV = std/mean) để đánh giá
        
        Args:
            embedding: Embedding vector cần đánh giá (List[float])
        
        Returns:
            float: Điểm chất lượng từ 0.0 đến 1.0, cao hơn là tốt hơn.
                Trả về 0.5 nếu có lỗi trong quá trình tính toán.
        
        Note:
            - Điểm 0.5 là điểm trung tính (neutral)
            - Điểm cao (>0.7) cho thấy embedding có chất lượng tốt
            - Điểm thấp (<0.3) có thể cho thấy embedding có vấn đề
            - Công thức này không phụ thuộc vào embedding dimension
        """
        try:
            vec = np.array(embedding, dtype=np.float64)
            
            # Tính các metrics cơ bản
            norm = np.linalg.norm(vec)
            mean_abs = np.mean(np.abs(vec))
            std_abs = np.std(np.abs(vec))
            variance = np.var(vec)
            
            # Kiểm tra edge cases
            if norm < 1e-10:  # Zero vector hoặc gần zero
                return 0.0
            
            if np.isnan(norm) or np.isinf(norm):
                logger.warning("Invalid norm detected in embedding")
                return 0.0
            
            # 1. Norm score (50% trọng số)
            # Phát hiện normalized models (norm ≈ 1.0)
            if 0.95 <= norm <= 1.05:
                # Normalized model: norm = 1.0 là lý tưởng
                norm_score = 1.0
            elif 0.9 <= norm <= 1.1:
                # Gần normalized: giảm điểm nhẹ
                norm_score = 0.9
            elif 0.5 <= norm <= 2.0:
                # Non-normalized nhưng hợp lý: sử dụng sigmoid
                # Norm trong khoảng 0.5-2.0 là tốt
                norm_score = 1.0 / (1.0 + np.exp(-2.0 * (norm - 1.0)))
            elif norm < 0.1:
                # Quá nhỏ → điểm thấp
                norm_score = norm / 0.1 * 0.3  # Scale từ 0 đến 0.3
            elif norm > 10.0:
                # Quá lớn → có thể là outlier
                norm_score = max(0.3, 1.0 - (norm - 10.0) / 10.0)
            else:
                # Khoảng giữa: sử dụng sigmoid mềm hơn
                norm_score = 1.0 / (1.0 + np.exp(-norm + 1.0))
            
            # Giới hạn norm_score trong [0, 1]
            norm_score = max(0.0, min(1.0, norm_score))
            
            # 2. Variance score (30% trọng số)
            # Variance hợp lý phụ thuộc vào norm và distribution
            # Với normalized vectors (norm ≈ 1), variance thường trong khoảng 0.01-0.1
            # Với non-normalized, variance phụ thuộc vào scale của values
            
            # Tính variance tương đối (relative variance)
            # Relative variance = variance / (mean^2) = (std/mean)^2
            if mean_abs > 1e-10:
                relative_variance = variance / (mean_abs ** 2)
                # Coefficient of variation
                cv = std_abs / mean_abs
                
                # CV hợp lý cho embeddings thường trong khoảng 0.5-2.0
                if 0.5 <= cv <= 2.0:
                    variance_score = 1.0
                elif cv < 0.5:
                    # Quá đều → có thể là constant vector
                    variance_score = cv / 0.5 * 0.7  # Scale từ 0 đến 0.7
                else:
                    # CV quá cao → có thể có outliers
                    variance_score = max(0.5, 1.0 - (cv - 2.0) / 5.0)
            else:
                # Mean quá nhỏ → variance score thấp
                variance_score = 0.3
            
            # Giới hạn variance_score trong [0, 1]
            variance_score = max(0.0, min(1.0, variance_score))
            
            # 3. Magnitude consistency score (20% trọng số)
            # Kiểm tra tính nhất quán của các giá trị
            # Sử dụng tỷ lệ giữa std và mean (coefficient of variation)
            if mean_abs > 1e-10:
                # CV hợp lý cho thấy distribution tốt
                cv = std_abs / mean_abs
                # CV trong khoảng 0.7-1.5 là tốt cho embeddings
                if 0.7 <= cv <= 1.5:
                    consistency_score = 1.0
                elif cv < 0.7:
                    # Quá đều
                    consistency_score = cv / 0.7 * 0.8
                else:
                    # Quá phân tán
                    consistency_score = max(0.5, 1.0 - (cv - 1.5) / 3.0)
            else:
                consistency_score = 0.3
            
            # Giới hạn consistency_score trong [0, 1]
            consistency_score = max(0.0, min(1.0, consistency_score))
            
            # Kết hợp các scores với trọng số
            # Norm quan trọng nhất (50%), variance (30%), consistency (20%)
            quality = (
                0.5 * norm_score +
                0.3 * variance_score +
                0.2 * consistency_score
            )
            
            # Giới hạn trong [0, 1]
            quality = max(0.0, min(1.0, quality))
            
            return float(quality)
        except Exception as e:
            logger.error(f"Quality score computation failed: {e}", exc_info=True)
            return 0.5  # Điểm trung tính mặc định

