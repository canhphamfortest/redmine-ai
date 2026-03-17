"""Module service embedding.

Module này cung cấp embedding service để tạo vector embeddings từ text:
- EmbeddingService: Class chính thực hiện embedding generation
- embedder: Singleton instance được sử dụng trong toàn bộ ứng dụng

Các chức năng chính:
- Embed text: Tạo embedding từ text đơn lẻ
- Embed batch: Tạo embeddings cho nhiều texts cùng lúc (hiệu quả hơn)
- Quality scoring: Tính điểm chất lượng của embedding
- Caching: Cache embeddings để tránh tính toán lại

Sử dụng sentence transformers model (mixedbread-ai/mxbai-embed-large-v1)
để tạo embeddings 1024-dimensional cho vector similarity search.
"""
from app.services.embedder.embedder import embedder, EmbeddingService

__all__ = ['embedder', 'EmbeddingService']

