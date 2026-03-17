"""Module Jobs API.

Module này cung cấp các endpoints cho quản lý scheduled jobs:
- CRUD operations: Create, read, update, delete scheduled jobs
- Job execution: Chạy job ngay lập tức và xem lịch sử execution
- Job scheduling: Quản lý cron expressions và next run times
- Job types: redmine_sync, git_sync, source_check

Jobs được thực thi bởi scheduler service và có thể được trigger thủ công.

Tất cả endpoints được định nghĩa trong router và được mount tại /api/jobs.
"""
from app.api.jobs.router import router

__all__ = ['router']

