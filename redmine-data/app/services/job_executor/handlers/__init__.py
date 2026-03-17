"""Các handler thực thi job.

Module này export tất cả job execution handlers:
- execute_redmine_sync: Handler cho redmine_sync job type
- execute_git_sync: Handler cho git_sync job type (placeholder, chưa implement)
- execute_source_check: Handler cho source_check job type
- execute_chunk_embedding: Handler tạo embeddings cho các chunks chờ xử lý

Mỗi handler nhận job config và thực thi job tương ứng.
Tất cả handlers được import từ các submodules và export qua __all__.
"""
from app.services.job_executor.handlers.redmine_handler import execute_redmine_sync
from app.services.job_executor.handlers.git_handler import execute_git_sync
from app.services.job_executor.handlers.source_check_handler import execute_source_check
from app.services.job_executor.handlers.embedding_handler import execute_chunk_embedding

__all__ = [
    'execute_redmine_sync',
    'execute_git_sync',
    'execute_source_check',
    'execute_chunk_embedding'
]

