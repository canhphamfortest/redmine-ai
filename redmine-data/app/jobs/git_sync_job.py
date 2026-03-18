"""Job đồng bộ files từ Git repository."""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.jobs.base_job import BaseJob, JobOption

logger = logging.getLogger(__name__)


class GitSyncJob(BaseJob):
    """Đồng bộ files từ Git repository vào hệ thống.

    TODO: Chưa được implement, hiện tại trả về kết quả rỗng.
    """

    name = "git_sync"
    label = "Git Sync"
    description = "Đồng bộ files từ Git repository vào hệ thống"

    def options(self) -> List[JobOption]:
        return [
            JobOption(
                key="repo_url",
                type="text",
                label="Repository URL",
                required=True,
                help="URL của Git repository cần sync",
                placeholder="https://github.com/org/repo.git",
            ),
            JobOption(
                key="branch",
                type="text",
                label="Branch",
                default="main",
                help="Branch cần sync",
                placeholder="main",
            ),
            JobOption(
                key="file_patterns",
                type="text",
                label="File Patterns",
                default=None,
                help="Chỉ sync các file khớp pattern (ví dụ: *.md, *.py). Phân cách bằng dấu phẩy.",
                placeholder="*.md, *.py",
            ),
        ]

    def execute(self, db: Session, execution_id: Optional[UUID] = None, **kwargs) -> Dict[str, Any]:
        """Thực thi Git sync.

        Args:
            db: Database session
            execution_id: UUID của JobExecution để check cancellation
            **kwargs: Config từ ScheduledJob.config:
                - repo_url (str, required): URL của Git repository
                - branch (str, default "main"): Branch cần sync
                - file_patterns (str, optional): Pattern filter files

        Returns:
            Dict chứa kết quả sync (hiện tại đều = 0 vì chưa implement)
        """
        from app.services.job_executor.exceptions import check_cancelled

        check_cancelled(execution_id, db)

        # TODO: Implement Git sync
        logger.warning("Git sync not yet implemented")

        return {
            "processed": 0,
            "created": 0,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }
