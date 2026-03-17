"""Module Search API.

Module này cung cấp các endpoints cho tìm kiếm và analytics:
- Vector search: Tìm kiếm semantic bằng vector embeddings
- RAG search: Tìm kiếm với RAG (Retrieval-Augmented Generation) và AI answer
- Related issues: Tìm các issues liên quan bằng AI analysis
- Analytics: Thống kê tìm kiếm, response times, popular queries
- History: Lịch sử tìm kiếm gần đây
- Usage: Thống kê OpenAI API usage và billing cycles

Tất cả endpoints được định nghĩa trong router và được mount tại /api/search.
"""
from app.api.search.router import router

__all__ = ['router']

