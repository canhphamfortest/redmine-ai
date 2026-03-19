"""Job đồng bộ issues và wiki từ Redmine project."""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.jobs.base_job import BaseJob, JobOption
from app.services.redmine import RedmineSync


class RedmineSyncJob(BaseJob):
    """Đồng bộ issues từ Redmine project vào database.

    Job này tạo Sources và Chunks từ Redmine issues.
    Embeddings sẽ được tạo riêng bởi ChunkEmbeddingJob.
    """

    name = "redmine_sync"
    label = "Redmine Sync"
    description = "Đồng bộ issues từ Redmine project vào hệ thống"

    def options(self) -> List[JobOption]:
        return [
            JobOption(
                key="project_identifier",
                type="text",
                label="Project Identifier",
                required=True,
                help="Project identifier (string) hoặc Project ID (số). Ví dụ: 'myproject' hoặc '123'",
                placeholder="myproject",
            ),
            JobOption(
                key="incremental",
                type="checkbox",
                label="Incremental Sync",
                default=True,
                help="Chỉ sync các issues đã cập nhật kể từ lần chạy trước",
            ),
            JobOption(
                key="filters.status",
                type="multiselect",
                label="Filter by Status",
                default=[],
                options=["New", "In Progress", "Resolved", "Closed"],
                help="Chỉ sync issues có status được chọn (bỏ trống = tất cả)",
            ),
            JobOption(
                key="filters.tracker",
                type="multiselect",
                label="Filter by Tracker",
                default=[],
                options=["Bug", "Feature", "Support", "Task"],
                help="Chỉ sync issues có tracker được chọn (bỏ trống = tất cả)",
            ),
        ]

    def execute(self, db: Session, execution_id: Optional[UUID] = None, **kwargs) -> Dict[str, Any]:
        """Thực thi Redmine sync.

        Args:
            db: Database session
            execution_id: UUID của JobExecution để check cancellation
            **kwargs: Config từ ScheduledJob.config:
                - project_identifier (str, required): Redmine project identifier
                - incremental (bool, default True): Chỉ sync issues đã cập nhật
                - filters (dict, optional): Bộ lọc bổ sung

        Returns:
            Dict chứa:
                - processed (int): Số issues đã xử lý
                - created (int): Số issues mới tạo
                - updated (int): Số issues đã cập nhật
                - failed (int): Số issues thất bại
                - errors (List[str]): Danh sách lỗi
        """
        # Hỗ trợ cả project_identifier và project_id (tương thích ngược)
        project_identifier = kwargs.get("project_identifier") or kwargs.get("project_id")

        if not project_identifier:
            raise ValueError("project_identifier is required in job config")

        # Build filters dict from dot-separated keys (e.g. "filters.status" → filters["status"]).
        # JobOption stores flat keys like "filters.status" in job.config; we also
        # accept a pre-built "filters" dict for backward compatibility.
        # Guard against legacy configs where "filters" may be stored as a non-dict
        # iterable (list, string) — fall back to empty dict to avoid ValueError.
        raw_filters = kwargs.get("filters")
        if isinstance(raw_filters, dict):
            filters: Dict[str, Any] = dict(raw_filters)
        else:
            if raw_filters is not None:
                logger.warning(
                    f"Unexpected type for 'filters' config key: {type(raw_filters).__name__}, ignoring"
                )
            filters: Dict[str, Any] = {}
        for key, value in kwargs.items():
            if key.startswith("filters.") and value:
                sub_key = key[len("filters."):]
                filters[sub_key] = value

        redmine_sync = RedmineSync()

        return redmine_sync.sync_project(
            project_id=project_identifier,
            incremental=kwargs.get("incremental", True),
            filters=filters,
            execution_id=execution_id,
        )


if __name__ == "__main__":
    RedmineSyncJob.run_cli()
