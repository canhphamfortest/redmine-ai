"""Module text chunker.

Module này cung cấp text chunking service để chia văn bản thành các chunks nhỏ hơn:
- TextChunker: Class chính thực hiện chunking cho nhiều loại nội dung
- chunker: Singleton instance được sử dụng trong toàn bộ ứng dụng

Hỗ trợ chunking cho:
- General text: Chia text thông thường với overlap
- Code: Chia code với context preservation (functions, classes)
- Redmine issues: Chia issue data với metadata chunk riêng
- Redmine wiki: Chia wiki pages với metadata chunk riêng

Mỗi chunk được tokenize và có thể được embed để tìm kiếm semantic.
"""
from app.services.chunker.chunker import TextChunker

# Singleton instance
chunker = TextChunker()

__all__ = ['TextChunker', 'chunker']

