"""Pydantic schemas cho Jobs API.

Module này định nghĩa các request/response schemas cho job management endpoints:
- JobCreate: Schema cho tạo scheduled job mới
- JobUpdate: Schema cho cập nhật scheduled job
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any


class JobCreate(BaseModel):
    """Schema cho request tạo scheduled job mới.
    
    Attributes:
        job_name: Tên của job (str)
        job_type: Loại job (str). Các giá trị hợp lệ:
                 - 'redmine_sync': Đồng bộ Redmine issues và wiki pages
                 - 'git_sync': Đồng bộ Git repositories
                 - 'source_check': Kiểm tra và cập nhật sources
                 - 'chunk_embedding': Tạo embeddings cho các chunks chờ xử lý
        cron_expression: Biểu thức cron để schedule job (str).
                        Ví dụ: "0 2 * * *" (chạy mỗi ngày lúc 2h sáng)
        config: Cấu hình job (dict, optional). Tùy thuộc vào job_type:
               - redmine_sync: {project_identifier hoặc project_id, filters}
               - git_sync: {repository_url, branch, paths, patterns}
               - source_check: {limit, project_key}
               - chunk_embedding: {limit, batch_size, source_type, project_key}
        is_active: Trạng thái active (bool, default: True).
                  Nếu False, job sẽ không được schedule
    """
    job_name: str
    job_type: str  # 'redmine_sync', 'git_sync', 'source_check', 'chunk_embedding'
    cron_expression: str
    config: Optional[Dict[str, Any]] = None
    is_active: bool = True


class JobUpdate(BaseModel):
    """Schema cho request cập nhật scheduled job.
    
    Attributes:
        job_name: Tên mới của job (str, optional)
        cron_expression: Biểu thức cron mới (str, optional)
        config: Cấu hình mới (dict, optional). Sẽ merge với config hiện có
        is_active: Trạng thái active mới (bool, optional)
    
    Note:
        - Tất cả fields đều optional, chỉ cập nhật các fields được cung cấp
        - Config được merge với config hiện có (không replace hoàn toàn)
    """
    job_name: Optional[str] = None
    cron_expression: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

