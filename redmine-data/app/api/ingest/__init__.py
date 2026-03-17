"""Ingest API module.

Module này cung cấp các endpoints cho việc ingest dữ liệu vào hệ thống:
- Manual upload: Upload và ingest files (PDF, DOCX, TXT, etc.)
- Redmine ingestion: Ingest Redmine issues và wiki pages
- Source management: List, check, và resync sources
- Statistics: Lấy thống kê ingestion (sources, documents, chunks, embeddings)

Tất cả endpoints được định nghĩa trong router và được mount tại /api/ingest.
"""
from app.api.ingest.router import router

__all__ = ['router']

