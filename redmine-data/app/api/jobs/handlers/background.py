"""Handler task background cho thực thi job"""
import logging
from app.database import SessionLocal
from app.models import ScheduledJob
from app.services.job_executor import JobExecutor

logger = logging.getLogger(__name__)


def execute_job_background(job_id: str, execution_id: str):
    """Task background để thực thi scheduled job.
    
    Hàm này được gọi bởi FastAPI BackgroundTasks để thực thi job trong background.
    Tạo database session mới và gọi JobExecutor để thực thi job.
    
    Args:
        job_id: UUID của scheduled job cần thực thi (string)
        execution_id: UUID của JobExecution record đã được tạo trước đó (string)
    
    Note:
        - Tạo database session mới cho background task
        - Session được đóng trong finally block
        - Lỗi được log nhưng không raise (background task)
        - JobExecution record được cập nhật bởi JobExecutor
    """
    db = SessionLocal()
    try:
        job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found for execution")
            return
        
        logger.info(f"Starting background execution for job: {job.job_name}")
        JobExecutor.execute_job(job, execution_id)
        
    except Exception as e:
        logger.error(f"Background job execution failed: {e}", exc_info=True)
    finally:
        db.close()

