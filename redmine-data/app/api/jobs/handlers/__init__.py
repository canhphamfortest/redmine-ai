"""Các handler Jobs API.

Module này export tất cả handlers cho Jobs API endpoints:
- CRUD handlers: list_jobs, create_job, get_job, update_job, delete_job
- Execution handlers: run_job_now, get_job_history

Tất cả handlers được import từ các submodules và export qua __all__.
"""
from app.api.jobs.handlers.crud import (
    list_jobs,
    create_job,
    get_job,
    update_job,
    delete_job
)
from app.api.jobs.handlers.execution import (
    run_job_now,
    get_job_history,
    cancel_execution
)

__all__ = [
    'list_jobs',
    'create_job',
    'get_job',
    'update_job',
    'delete_job',
    'run_job_now',
    'get_job_history',
    'cancel_execution'
]

