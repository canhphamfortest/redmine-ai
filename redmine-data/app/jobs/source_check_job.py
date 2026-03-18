"""Job kiểm tra sources có cần sync lại không."""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.jobs.base_job import BaseJob, JobOption
from app.services.check_source import SourceChecker

logger = logging.getLogger(__name__)


class SourceCheckJob(BaseJob):
    """Kiểm tra sources có bị outdated và cần sync lại không.

    Job này dùng SourceChecker service để so sánh nội dung hiện tại
    với bản gốc và đánh dấu những sources cần re-sync.
    """

    name = "source_check"
    label = "Source Check"
    description = "Kiểm tra sources có cần sync lại không"

    def options(self) -> List[JobOption]:
        return [
            JobOption(
                key="limit",
                type="number",
                label="Limit",
                default=1000,
                help="Số lượng sources tối đa để kiểm tra mỗi lần chạy (0 = không giới hạn)",
            ),
            JobOption(
                key="project_id",
                type="text",
                label="Project ID",
                default=None,
                help="Chỉ kiểm tra sources thuộc project này (bỏ trống = tất cả projects)",
                placeholder="myproject",
            ),
        ]

    def execute(self, db: Session, execution_id: Optional[UUID] = None, **kwargs) -> Dict[str, Any]:
        """Thực thi kiểm tra sources.

        Args:
            db: Database session
            execution_id: UUID của JobExecution để check cancellation
            **kwargs: Config từ ScheduledJob.config:
                - limit (int, default 1000): Số sources tối đa kiểm tra
                - project_id (str, optional): Filter theo project

        Returns:
            Dict chứa:
                - processed (int): Số sources đã kiểm tra
                - outdated (int): Số sources outdated
                - up_to_date (int): Số sources vẫn còn mới
                - failed (int): Số sources kiểm tra thất bại
                - errors (List[str]): Danh sách lỗi
        """
        from app.services.job_executor.exceptions import check_cancelled

        check_cancelled(execution_id, db)

        limit = kwargs.get("limit")
        if limit is None:
            limit = 1000
        elif not isinstance(limit, int) or limit < 0:
            raise ValueError(f"Invalid limit: {limit}. Must be non-negative integer.")
        # 0 = không giới hạn → truyền None cho SourceChecker
        if limit == 0:
            limit = None

        project_id = kwargs.get("project_id")
        if project_id is not None and not isinstance(project_id, str):
            raise ValueError(f"Invalid project_id: {project_id}. Must be string.")

        source_checker = SourceChecker()
        result = source_checker.check_sources(
            limit=limit,
            project_id=project_id,
            execution_id=execution_id,
        )

        # Map keys từ SourceChecker format sang format chuẩn
        return {
            "processed": result.get("checked", 0),
            "outdated": result.get("outdated", 0),
            "up_to_date": result.get("up_to_date", 0),
            "failed": result.get("failed", 0),
            "errors": result.get("errors", []),
        }
