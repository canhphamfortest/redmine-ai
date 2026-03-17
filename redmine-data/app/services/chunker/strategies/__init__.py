"""Các chiến lược chunking.

Module này chứa các chiến lược chunking khác nhau cho các loại nội dung:
- chunk_text: Chia text thông thường với overlap
- chunk_code: Chia code với context preservation (functions, classes)
- chunk_redmine_issue: Chia Redmine issue data với metadata chunk riêng
- chunk_redmine_wiki: Chia Redmine wiki page với metadata chunk riêng

Mỗi strategy được tối ưu cho loại nội dung cụ thể để đảm bảo:
- Chunks có kích thước phù hợp cho embedding
- Context được preserve (đặc biệt cho code)
- Metadata được tách riêng để tìm kiếm tốt hơn
"""
from app.services.chunker.strategies.text_chunker import chunk_text
from app.services.chunker.strategies.code_chunker import chunk_code
from app.services.chunker.strategies.issue_chunker import chunk_redmine_issue
from app.services.chunker.strategies.wiki_chunker import chunk_redmine_wiki

__all__ = [
    'chunk_text',
    'chunk_code',
    'chunk_redmine_issue',
    'chunk_redmine_wiki'
]

