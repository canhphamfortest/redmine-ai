"""Handler job sync Redmine.

Module này cung cấp function để thực thi redmine_sync job:
- execute_redmine_sync: Thực thi Redmine synchronization cho project
- Job configuration: Đọc config từ job (project_identifier hoặc project_id, filters)
- Result reporting: Trả về kết quả sync (items processed, failed)
- Cancellation support: Hỗ trợ cancel job execution đang chạy

Lưu ý: redmine_sync giờ chỉ tạo nguồn và chunks; embeddings sẽ được tạo bởi
job chunk_embedding riêng.
"""
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.models import ScheduledJob
from app.services.redmine import RedmineSync


def execute_redmine_sync(job: ScheduledJob, db: Session, execution_id: Optional[UUID] = None) -> Dict[str, Any]:
    """Thực thi scheduled job để đồng bộ Redmine project.
    
    Hàm này được gọi bởi JobExecutor để thực thi job loại 'redmine_sync'.
    Đọc cấu hình từ job.config và gọi RedmineSync để sync project.
    
    Args:
        job: ScheduledJob instance chứa cấu hình sync
        db: Database session (không được sử dụng trực tiếp trong hàm này)
        execution_id: ID của JobExecution để check cancellation (tùy chọn)
    
    Returns:
        Dict[str, Any]: Dictionary chứa kết quả sync từ RedmineSync.sync_project():
            - processed: Số lượng issues đã xử lý (int)
            - created: Số lượng issues mới được tạo (int)
            - updated: Số lượng issues đã cập nhật (int)
            - failed: Số lượng issues thất bại (int)
            - errors: Danh sách error messages (List[str])
    
    Note:
        - Config được đọc từ job.config dictionary
        - project_identifier: Redmine project identifier (string, ưu tiên)
        - project_id: Redmine project ID hoặc identifier (string, fallback nếu không có project_identifier)
        - incremental: True để chỉ sync issues đã cập nhật (mặc định: True)
        - filters: Dictionary chứa các bộ lọc bổ sung (status_id, tracker_id, etc.)
        - execution_id được truyền xuống RedmineSync.sync_project() để check cancellation
    """
    config = job.config or {}
    
    # Hỗ trợ cả project_identifier và project_id (tương thích ngược)
    project_identifier = config.get('project_identifier') or config.get('project_id')
    
    if not project_identifier:
        raise ValueError("project_identifier or project_id is required in job config")
    
    redmine_sync = RedmineSync()
    
    result = redmine_sync.sync_project(
        project_id=project_identifier,
        incremental=config.get('incremental', True),
        filters=config.get('filters', {}),
        execution_id=execution_id
    )
    
    return result

