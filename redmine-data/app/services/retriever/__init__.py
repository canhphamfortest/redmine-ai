"""Module retriever cho search service.

Module này cung cấp retrieval services để tìm kiếm:
- VectorRetriever: Class chính thực hiện hybrid search (vector + keyword)
- retriever: Singleton instance được sử dụng trong toàn bộ ứng dụng

Các chức năng chính:
- Hybrid search: Kết hợp vector similarity và full-text search
- Vector search: Tìm kiếm chunks bằng vector similarity (cosine distance)
- Keyword search: Tìm kiếm chunks bằng full-text search (PostgreSQL FTS)
- Search by embedding: Tìm kiếm trực tiếp bằng embedding vector
- Result formatting: Format kết quả với metadata và similarity/RRF scores

Sử dụng pgvector cho vector search và GIN index cho full-text search.
"""
from app.services.retriever.retriever import VectorRetriever
from app.services.retriever.hybrid_search import hybrid_search, merge_with_rrf
from app.services.retriever.keyword_search import keyword_search, remove_stopwords, build_fts_query
from app.services.retriever.vector_search import vector_search_by_query, vector_search_by_embedding

# Instance singleton
retriever = VectorRetriever()

__all__ = [
    'VectorRetriever',
    'retriever',
    'hybrid_search',
    'merge_with_rrf',
    'keyword_search',
    'remove_stopwords',
    'build_fts_query',
    'vector_search_by_query',
    'vector_search_by_embedding',
]

