"""RAG System Application Package.

Package chính của RAG (Retrieval-Augmented Generation) System.

Hệ thống này cung cấp:
- Content ingestion: Ingest dữ liệu từ Redmine, Git, và manual uploads
- Vector search: Tìm kiếm semantic bằng vector embeddings
- RAG: Tạo câu trả lời AI dựa trên retrieved context
- Job scheduling: Tự động sync và check sources
- Analytics: Thống kê usage, search, và costs

Các module chính:
- api: FastAPI endpoints cho ingestion, search, jobs, config
- services: Core services (chunker, embedder, retriever, RAG chain)
- models: Database models (SQLAlchemy)
- schedulers: Job scheduler service
"""

