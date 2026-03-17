"""Router cho Jobs API.

Module này định nghĩa các endpoints cho quản lý scheduled jobs:
- CRUD operations: Create, read, update, delete jobs
- Job execution: Chạy job ngay lập tức và xem lịch sử execution
- Job scheduling: Quản lý cron expressions và next run times
"""
from fastapi import APIRouter

from app.api.jobs.handlers import (
    list_jobs,
    create_job,
    get_job,
    update_job,
    delete_job,
    run_job_now,
    get_job_history,
    cancel_execution
)

router = APIRouter()

# Đăng ký endpoints
router.add_api_route("/", list_jobs, methods=["GET"])
router.add_api_route("/", create_job, methods=["POST"])
router.add_api_route("/{job_id}", get_job, methods=["GET"])
router.add_api_route("/{job_id}", update_job, methods=["PUT"])
router.add_api_route("/{job_id}", delete_job, methods=["DELETE"])
router.add_api_route("/{job_id}/run", run_job_now, methods=["POST"])
router.add_api_route("/{job_id}/history", get_job_history, methods=["GET"])
router.add_api_route("/executions/{execution_id}/cancel", cancel_execution, methods=["POST"])

