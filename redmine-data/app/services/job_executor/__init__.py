"""Module service thực thi job.

Module này cung cấp job execution service để thực thi scheduled jobs:
- JobExecutor: Class chính thực hiện job execution

Các chức năng chính:
- Execute jobs: Thực thi các scheduled jobs dựa trên job_type
- Job handlers: Xử lý các loại jobs khác nhau (redmine_sync, git_sync, source_check)
- Execution logging: Ghi log execution history và kết quả
- Error handling: Xử lý lỗi và retry logic

Jobs được trigger bởi scheduler service và có thể được thực thi thủ công qua API.
"""
from app.services.job_executor.executor import JobExecutor

__all__ = ['JobExecutor']

