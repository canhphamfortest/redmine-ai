"""Handler job kiểm tra source.

Module này cung cấp function để thực thi source_check job:
- execute_source_check: Thực thi source checking với limits và filters
- Job configuration: Đọc config từ job (limit, project_key)
- Result reporting: Trả về kết quả check (sources checked, outdated, resynced)
- Cancellation support: Hỗ trợ cancel job execution đang chạy

Sử dụng SourceChecker service để thực hiện checking operations.
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models import ScheduledJob
from app.services.check_source import SourceChecker

logger = logging.getLogger(__name__)


def execute_source_check(job: ScheduledJob, db: Session, execution_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Thực thi scheduled job để kiểm tra sources có cần sync lại không.
    
    Hàm này được gọi bởi JobExecutor để thực thi job loại 'source_check'.
    Đọc cấu hình từ job.config và gọi SourceChecker để kiểm tra sources.
    
    Args:
        job: ScheduledJob instance chứa cấu hình check
        db: Database session (không được sử dụng trực tiếp trong hàm này)
        execution_id: ID của JobExecution để check cancellation (tùy chọn)
    
    Returns:
        Dict[str, Any]: Dictionary chứa kết quả check (đã được map keys):
            - processed: Số lượng sources đã kiểm tra (int)
            - outdated: Số lượng sources đã outdated (int)
            - up_to_date: Số lượng sources vẫn còn up-to-date (int)
            - failed: Số lượng sources kiểm tra thất bại (int)
            - errors: Danh sách error messages (List[str])
    
    Raises:
        ValueError: Nếu limit không phải là số nguyên dương hoặc project_id không phải string
        JobCancelledException: Nếu execution bị cancel trong quá trình check
    
    Note:
        - Config được đọc từ job.config dictionary
        - limit: Số lượng sources tối đa để kiểm tra (mặc định: 1000)
        - project_id: Project identifier để filter sources (tùy chọn)
        - Keys được map từ SourceChecker format sang job execution format
        - execution_id được truyền xuống SourceChecker.check_sources() để check cancellation
    """
    # Import locally để tránh circular import
    from app.services.job_executor.executor import JobExecutor, JobCancelledException
    
    # Kiểm tra cancellation trước khi bắt đầu
    if execution_id and JobExecutor.is_execution_cancelled(execution_id, db):
        logger.info(f"Source check cancelled before starting for execution {execution_id}")
        raise JobCancelledException("Job execution was cancelled")
    
    config = job.config or {}
    
    # Lấy limit với xử lý None đúng cách
    limit = config.get('limit')
    if limit is None:
        limit = 1000  # Giới hạn mặc định
    elif not isinstance(limit, int) or limit <= 0:
        raise ValueError(f"Invalid limit: {limit}. Must be positive integer.")
    
    # Xác thực project_id nếu được cung cấp
    project_id = config.get('project_id')
    if project_id is not None and not isinstance(project_id, str):
        raise ValueError(f"Invalid project_id: {project_id}. Must be string.")
    
    source_checker = SourceChecker()
    
    result = source_checker.check_sources(
        limit=limit,
        project_id=project_id,
        execution_id=execution_id
    )
    
    # Đổi tên keys để khớp với định dạng mong đợi
    return {
        'processed': result.get('checked', 0),
        'outdated': result.get('outdated', 0),
        'up_to_date': result.get('up_to_date', 0),
        'failed': result.get('failed', 0),
        'errors': result.get('errors', [])
    }

