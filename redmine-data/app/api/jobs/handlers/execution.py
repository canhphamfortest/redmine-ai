"""Các handler thực thi job"""
import logging
from fastapi import Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime

from app.database import get_db
from app.models import ScheduledJob, JobExecution
from app.api.jobs.handlers.background import execute_job_background

logger = logging.getLogger(__name__)


async def run_job_now(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Kích hoạt thực thi scheduled job ngay lập tức (không đợi cron schedule).
    
    Endpoint này cho phép chạy một job ngay lập tức mà không cần đợi đến
    thời gian schedule. Job sẽ được thực thi trong background task.
    
    Args:
        job_id: UUID của scheduled job cần chạy (string)
        background_tasks: FastAPI BackgroundTasks để thực thi job trong background
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - execution_id: UUID của JobExecution record đã tạo (str)
            - status: "triggered"
            - message: "Job execution started"
    
    Raises:
        HTTPException:
            - HTTP 404 nếu job không tồn tại
            - HTTP 500 nếu có lỗi trong quá trình kích hoạt job
    
    Note:
        - Tạo JobExecution record với status="running" trước khi thực thi
        - Job được thực thi trong background task để không block API response
        - JobExecution record sẽ được cập nhật bởi JobExecutor khi job hoàn thành
    """
    try:
        job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Tạo bản ghi execution
        execution = JobExecution(
            job_id=job.id,
            started_at=datetime.now(),
            status="running"
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)
        
        # Kích hoạt thực thi job thực tế trong background
        logger.info(f"Triggering manual execution for job: {job.job_name} (execution_id: {execution.id})")
        background_tasks.add_task(execute_job_background, str(job.id), str(execution.id))
        
        return {
            "execution_id": str(execution.id),
            "status": "triggered",
            "message": "Job execution started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to run job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def get_job_history(
    job_id: str,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Lấy lịch sử thực thi của một scheduled job.
    
    Endpoint này trả về danh sách các lần thực thi (JobExecution) của một job,
    bao gồm thông tin về thời gian, trạng thái, và kết quả.
    
    Args:
        job_id: UUID của scheduled job cần lấy lịch sử (string)
        limit: Số lượng execution records tối đa trả về (mặc định: 20)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - history: Danh sách lịch sử thực thi (List[Dict]):
                - id: UUID của execution record (str)
                - started_at: Thời gian bắt đầu thực thi (str, ISO format)
                - completed_at: Thời gian hoàn thành (str, ISO format, optional)
                - status: Trạng thái execution ("running", "completed", "failed", "cancelled") (str)
                - items_processed: Số lượng items đã xử lý (int, optional)
                - items_failed: Số lượng items thất bại (int, optional)
                - error_message: Thông báo lỗi nếu có (str, optional)
    
    Raises:
        HTTPException: HTTP 500 nếu có lỗi trong quá trình lấy lịch sử
    
    Note:
        - Lịch sử được sắp xếp theo started_at giảm dần (mới nhất trước)
        - Chỉ lấy các execution records của job cụ thể
    """
    try:
        executions = db.query(JobExecution)\
            .filter(JobExecution.job_id == job_id)\
            .order_by(JobExecution.started_at.desc())\
            .limit(limit)\
            .all()
        
        return {
            "history": [
                {
                    "id": str(ex.id),
                    "started_at": ex.started_at.isoformat(),
                    "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
                    "status": ex.status,
                    "items_processed": ex.items_processed,
                    "items_failed": ex.items_failed,
                    "error_message": ex.error_message
                }
                for ex in executions
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get job history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def cancel_execution(
    execution_id: str,
    db: Session = Depends(get_db)
):
    """Cancel một job execution đang chạy.
    
    Endpoint này cho phép cancel một job execution đang ở trạng thái "running".
    Execution sẽ được đánh dấu là "cancelled" trong database, và job đang chạy
    sẽ phát hiện cancellation flag và dừng lại tại điểm check tiếp theo.
    
    Args:
        execution_id: UUID của JobExecution cần cancel (string)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - execution_id: UUID của execution đã cancel (str)
            - status: "cancelled"
            - message: Thông báo kết quả cancel
    
    Raises:
        HTTPException:
            - HTTP 404 nếu execution không tồn tại
            - HTTP 400 nếu execution không ở trạng thái "running"
            - HTTP 500 nếu có lỗi trong quá trình cancel
    
    Note:
        - Chỉ có thể cancel execution có status="running"
        - Execution đã completed hoặc failed không thể cancel
        - Job đang chạy sẽ check cancellation flag định kỳ và dừng khi phát hiện
        - Cancellation không force stop ngay lập tức, job sẽ dừng tại điểm check tiếp theo
    """
    try:
        execution = db.query(JobExecution).filter(JobExecution.id == execution_id).first()
        
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        # Chỉ có thể cancel execution đang chạy
        if execution.status != "running":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel execution with status '{execution.status}'. Only 'running' executions can be cancelled."
            )
        
        # Update execution status thành "cancelled"
        execution.status = "cancelled"
        execution.completed_at = datetime.now()
        execution.error_message = "Job execution was cancelled by user request"
        db.commit()
        db.refresh(execution)
        
        logger.info(f"Cancelled execution: {execution_id}")
        
        return {
            "execution_id": str(execution.id),
            "status": "cancelled",
            "message": "Job execution cancellation requested. The job will stop at the next cancellation check point."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel execution: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

