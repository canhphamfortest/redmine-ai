"""Exceptions cho job execution system."""
import logging
from typing import Optional, Union
from uuid import UUID

logger = logging.getLogger(__name__)


class JobCancelledException(Exception):
    """Raise khi job execution bị cancel bởi user request."""
    pass


def check_cancelled(execution_id: Optional[Union[str, UUID]], db) -> None:
    """Kiểm tra execution có bị cancel không, raise nếu có.

    Args:
        execution_id: UUID của JobExecution cần kiểm tra
        db: Database session

    Raises:
        JobCancelledException: Nếu execution đã bị cancel
    """
    if not execution_id:
        return

    from app.models import JobExecution

    try:
        if isinstance(execution_id, str):
            execution_id = UUID(execution_id)

        execution = db.query(JobExecution).filter(JobExecution.id == execution_id).first()
        if execution and execution.status == "cancelled":
            raise JobCancelledException(f"Execution {execution_id} was cancelled by user")
    except JobCancelledException:
        raise
    except Exception:
        logger.exception(
            "Failed to check cancellation for execution %s",
            execution_id,
        )
        raise
