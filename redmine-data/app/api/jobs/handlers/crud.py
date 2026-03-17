"""Các handler CRUD cho API Jobs"""
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from croniter import croniter

from app.database import get_db
from app.models import ScheduledJob
from app.api.jobs.schemas import JobCreate, JobUpdate
from app.config import settings

logger = logging.getLogger(__name__)


async def list_jobs(
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Liệt kê tất cả các scheduled jobs với filter tùy chọn.
    
    Endpoint này trả về danh sách tất cả scheduled jobs trong hệ thống.
    Có thể filter theo trạng thái active/inactive.
    
    Args:
        is_active: Filter theo trạng thái active (tùy chọn).
                   True = chỉ jobs đang active, False = chỉ jobs inactive,
                   None = tất cả jobs
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - jobs: Danh sách jobs (List[Dict]):
                - id: UUID của job (str)
                - job_name: Tên job (str)
                    - job_type: Loại job (redmine_sync, git_sync, source_check, chunk_embedding) (str)
                - cron_expression: Biểu thức cron (str)
                - is_active: Trạng thái active (bool)
                - config: Cấu hình job (dict)
                - last_run_at: Thời gian chạy cuối (str, ISO format, optional)
                - next_run_at: Thời gian chạy tiếp theo (str, ISO format, optional)
                - created_at: Thời gian tạo (str, ISO format)
    
    Raises:
        HTTPException: HTTP 500 nếu có lỗi trong quá trình query
    
    Note:
        - Jobs được sắp xếp theo created_at giảm dần (mới nhất trước)
    """
    try:
        query = db.query(ScheduledJob)
        
        if is_active is not None:
            query = query.filter(ScheduledJob.is_active == is_active)
        
        jobs = query.order_by(ScheduledJob.created_at.desc()).all()
        
        return {
            "jobs": [
                {
                    "id": str(job.id),
                    "job_name": job.job_name,
                    "job_type": job.job_type,
                    "cron_expression": job.cron_expression,
                    "is_active": job.is_active,
                    "config": job.config,
                    "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
                    "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
                    "created_at": job.created_at.isoformat()
                }
                for job in jobs
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def create_job(
    job_data: JobCreate,
    db: Session = Depends(get_db)
):
    """Tạo một scheduled job mới.
    
    Endpoint này tạo một scheduled job mới với cron expression và cấu hình.
    Cron expression được validate và next_run_at được tính toán tự động.
    
    Args:
        job_data: JobCreate schema chứa thông tin job:
            - job_name: Tên job (str)
            - job_type: Loại job (redmine_sync, git_sync, source_check, chunk_embedding) (str)
            - cron_expression: Biểu thức cron (str)
            - config: Cấu hình job (dict, optional)
            - is_active: Trạng thái active (bool, mặc định: True)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - id: UUID của job đã tạo (str)
            - job_name: Tên job (str)
            - status: "created"
            - next_run_at: Thời gian chạy tiếp theo (str, ISO format)
    
    Raises:
        HTTPException:
            - HTTP 400 nếu cron expression không hợp lệ
            - HTTP 500 nếu có lỗi trong quá trình tạo job
    
    Note:
        - Cron expression được validate bằng croniter.is_valid()
        - next_run_at được tính toán từ cron expression và current time
        - Job sẽ được scheduler tự động load và schedule
    """
    try:
        # Xác thực cron expression
        if not croniter.is_valid(job_data.cron_expression):
            raise HTTPException(status_code=400, detail="Invalid cron expression")
        
        # Tính toán lần chạy tiếp theo
        # Cron expression được hiểu theo local timezone
        local_tz = ZoneInfo(settings.scheduler_timezone)
        now_local = datetime.now(local_tz)
        cron = croniter(job_data.cron_expression, now_local)
        next_run_local = cron.get_next(datetime)
        
        # Đảm bảo next_run_local có local timezone
        if next_run_local.tzinfo is None:
            next_run_local = next_run_local.replace(tzinfo=local_tz)
        
        # Convert sang UTC để lưu vào database
        next_run_utc = next_run_local.astimezone(timezone.utc)
        
        # Tạo job
        job = ScheduledJob(
            job_name=job_data.job_name,
            job_type=job_data.job_type,
            cron_expression=job_data.cron_expression,
            config=job_data.config,
            is_active=job_data.is_active,
            next_run_at=next_run_utc
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        logger.info(f"Created job: {job.job_name} ({job.id})")
        
        return {
            "id": str(job.id),
            "job_name": job.job_name,
            "status": "created",
            "next_run_at": job.next_run_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Lấy chi tiết một scheduled job.
    
    Endpoint này trả về thông tin chi tiết của một job cụ thể.
    
    Args:
        job_id: UUID của job cần lấy (string)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa thông tin job:
            - id: UUID của job (str)
            - job_name: Tên job (str)
            - job_type: Loại job (str)
            - cron_expression: Biểu thức cron (str)
            - is_active: Trạng thái active (bool)
            - config: Cấu hình job (dict)
            - last_run_at: Thời gian chạy cuối (str, ISO format, optional)
            - next_run_at: Thời gian chạy tiếp theo (str, ISO format, optional)
            - created_at: Thời gian tạo (str, ISO format)
    
    Raises:
        HTTPException:
            - HTTP 404 nếu job không tồn tại
            - HTTP 500 nếu có lỗi trong quá trình query
    """
    try:
        job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "id": str(job.id),
            "job_name": job.job_name,
            "job_type": job.job_type,
            "cron_expression": job.cron_expression,
            "is_active": job.is_active,
            "config": job.config,
            "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
            "next_run_at": job.next_run_at.isoformat() if job.next_run_at else None,
            "created_at": job.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def update_job(
    job_id: str,
    job_data: JobUpdate,
    db: Session = Depends(get_db)
):
    """Cập nhật một scheduled job.
    
    Endpoint này cập nhật thông tin của một job. Chỉ các trường được cung cấp
    trong job_data mới được cập nhật. Nếu cron_expression được cập nhật,
    next_run_at sẽ được tính toán lại.
    
    Args:
        job_id: UUID của job cần cập nhật (string)
        job_data: JobUpdate schema chứa các trường cần cập nhật:
            - job_name: Tên job mới (str, optional)
            - cron_expression: Biểu thức cron mới (str, optional)
            - config: Cấu hình job mới (dict, optional)
            - is_active: Trạng thái active mới (bool, optional)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - id: UUID của job đã cập nhật (str)
            - status: "updated"
    
    Raises:
        HTTPException:
            - HTTP 404 nếu job không tồn tại
            - HTTP 400 nếu cron expression không hợp lệ
            - HTTP 500 nếu có lỗi trong quá trình cập nhật
    
    Note:
        - Chỉ các trường được cung cấp mới được cập nhật (partial update)
        - Nếu cron_expression được cập nhật, next_run_at được tính toán lại
        - Job sẽ được scheduler tự động reload nếu đang active
    """
    try:
        job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Cập nhật các trường
        if job_data.job_name:
            job.job_name = job_data.job_name
        
        if job_data.cron_expression:
            if not croniter.is_valid(job_data.cron_expression):
                raise HTTPException(status_code=400, detail="Invalid cron expression")
            
            job.cron_expression = job_data.cron_expression
            # Cron expression được hiểu theo local timezone
            local_tz = ZoneInfo(settings.scheduler_timezone)
            now_local = datetime.now(local_tz)
            cron = croniter(job_data.cron_expression, now_local)
            next_run_local = cron.get_next(datetime)
            
            # Đảm bảo next_run_local có local timezone
            if next_run_local.tzinfo is None:
                next_run_local = next_run_local.replace(tzinfo=local_tz)
            
            # Convert sang UTC để lưu vào database
            job.next_run_at = next_run_local.astimezone(timezone.utc)
        
        if job_data.config is not None:
            job.config = job_data.config
        
        if job_data.is_active is not None:
            job.is_active = job_data.is_active
        
        db.commit()
        db.refresh(job)
        
        logger.info(f"Updated job: {job.job_name} ({job.id})")
        
        return {
            "id": str(job.id),
            "status": "updated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def delete_job(
    job_id: str,
    db: Session = Depends(get_db)
):
    """Xóa một scheduled job.
    
    Endpoint này xóa một job khỏi database. Job sẽ không còn được schedule
    sau khi xóa.
    
    Args:
        job_id: UUID của job cần xóa (string)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - status: "deleted"
    
    Raises:
        HTTPException:
            - HTTP 404 nếu job không tồn tại
            - HTTP 500 nếu có lỗi trong quá trình xóa
    
    Note:
        - Job sẽ được scheduler tự động remove khỏi schedule
        - Không thể undo sau khi xóa
    """
    try:
        job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        db.delete(job)
        db.commit()
        
        logger.info(f"Deleted job: {job_id}")
        
        return {"status": "deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete job: {e}")
        raise HTTPException(status_code=500, detail=str(e))

