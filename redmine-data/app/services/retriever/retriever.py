"""Lớp retriever chính.

Module này cung cấp VectorRetriever class để thực hiện search:
- Hybrid search: Kết hợp vector search và keyword search (mặc định)
- Vector search: Tìm kiếm chunks bằng vector embeddings (cosine similarity)
- Search by embedding: Tìm kiếm trực tiếp bằng embedding vector

Sử dụng pgvector trong PostgreSQL cho vector search và full-text search cho keywords.
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.config import settings
from app.services.retriever.vector_search import vector_search_by_query, vector_search_by_embedding
from app.services.retriever.hybrid_search import hybrid_search

logger = logging.getLogger(__name__)


class VectorRetriever:
    """Truy xuất các chunk liên quan bằng vector similarity search.
    
    Class này cung cấp các phương thức để tìm kiếm chunks liên quan bằng cách
    sử dụng vector embeddings. Hỗ trợ tìm kiếm từ query text hoặc embedding vector
    trực tiếp.
    
    Attributes:
        top_k: Số lượng kết quả mặc định (int)
        similarity_threshold: Ngưỡng similarity tối thiểu (float)
    """
    
    def __init__(self, top_k: int = None, similarity_threshold: float = None):
        """Khởi tạo VectorRetriever.
        
        Args:
            top_k: Số lượng kết quả mặc định. Nếu None, sử dụng settings.similarity_top_k
            similarity_threshold: Ngưỡng similarity tối thiểu. Nếu None, sử dụng settings.similarity_threshold
        """
        self.top_k = top_k or settings.similarity_top_k
        self.similarity_threshold = similarity_threshold or settings.similarity_threshold
    
    def search(
        self,
        query: str,
        db: Session,
        top_k: int = None,
        project_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """Tìm kiếm bằng hybrid search (vector + keyword).
        
        Hàm này kết hợp vector search (semantic) và keyword search (full-text)
        để tìm các chunks liên quan. Kết quả được merge bằng RRF (Reciprocal
        Rank Fusion) để lấy những chunks tốt nhất từ cả hai phương pháp.
        
        Args:
            query: Văn bản truy vấn tìm kiếm (string)
            db: Database session
            top_k: Số lượng kết quả trả về. Nếu None, sử dụng self.top_k
        
        Returns:
            List[Dict[str, Any]]: Danh sách các chunk liên quan, mỗi chunk chứa:
                - text: Nội dung chunk (str)
                - metadata: Metadata của chunk (dict)
                - similarity_score: Điểm similarity (float, 0-1, optional)
                - rrf_score: Điểm RRF từ hybrid search (float, optional)
                - chunk_id: ID của chunk (str, optional)
        
        Note:
            - Kết hợp vector search (semantic) và keyword search (exact match)
            - Chunks xuất hiện ở cả 2 kết quả sẽ có rank cao hơn
            - Nếu keyword search không có kết quả (query chỉ có stopwords),
              fallback về vector-only results
        """
        k = top_k or self.top_k
        return vector_search_by_query(query, db, k, self.similarity_threshold, project_ids)
    
    def search_by_embedding(
        self,
        embedding_vector: List[float],
        db: Session,
        top_k: int = None,
        exclude_source_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Tìm kiếm bằng vector embedding trực tiếp (không cần tạo embedding từ văn bản).
        
        Hàm này tìm kiếm các chunks tương tự bằng cách sử dụng embedding vector
        đã có sẵn. Hữu ích khi đã có embedding (ví dụ: từ một issue khác) và muốn
        tìm các chunks tương tự.
        
        Args:
            embedding_vector: Vector embedding để tìm kiếm (List[float])
            db: Database session
            top_k: Số lượng kết quả trả về. Nếu None, sử dụng self.top_k
            exclude_source_ids: Danh sách source IDs để loại trừ khỏi kết quả (List[str], optional).
                               Hữu ích để loại trừ source hiện tại khi tìm related items
        
        Returns:
            List[Dict[str, Any]]: Danh sách các chunk liên quan, mỗi chunk chứa:
                - text: Nội dung chunk (str)
                - metadata: Metadata của chunk (dict)
                - similarity_score: Điểm similarity (float, 0-1)
                - chunk_id: ID của chunk (str, optional)
                - source_id: ID của source (str, optional)
        
        Note:
            - Embedding vector phải có kích thước khớp với embedding model
            - Chunks từ các sources trong exclude_source_ids sẽ bị loại trừ
            - Chunks được sắp xếp theo similarity score giảm dần
            - Chỉ trả về chunks có similarity >= similarity_threshold
        """
        k = top_k or self.top_k
        return vector_search_by_embedding(
            embedding_vector, db, k, self.similarity_threshold, exclude_source_ids
        )
    

