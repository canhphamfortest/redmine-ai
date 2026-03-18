"""Service thực thi job chính.

Module này cung cấp JobExecutor class để thực thi scheduled jobs:
- Job execution: Thực thi các scheduled jobs dựa trên job_type
- Job registry: Tự động discover các job types từ app/jobs/
- Execution logging: Ghi log execution history và kết quả
- Error handling: Xử lý lỗi và retry logic
- Cancellation support: Hỗ trợ cancel job execution đang chạy

Jobs được trigger bởi scheduler service và có thể được thực thi thủ công qua API.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Union, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ScheduledJob, JobExecution
from app.services.job_executor.exceptions import JobCancelledException, check_cancelled
from app.jobs.registry import JOB_REGISTRY

logger = logging.getLogger(__name__)

# Re-export để backward compatibility
__all__ = ["JobExecutor", "JobCancelledException"]


class JobExecutor:
    """Thực thi các scheduled jobs với tracking và error handling.
    
    Class này xử lý việc thực thi các jobs đã được lên lịch, bao gồm:
    - Tạo và cập nhật execution records
    - Gọi handler phù hợp dựa trên job type
    - Track progress và errors
    - Cập nhật job last_run_at
    - Hỗ trợ cancellation của job execution đang chạy
    
    Note:
        - Static class, không cần khởi tạo instance
        - Hỗ trợ các job types: redmine_sync, git_sync, source_check, chunk_embedding
    """
    
    @staticmethod
    def is_execution_cancelled(execution_id: Union[str, UUID], db: Optional[Session] = None) -> bool:
        """Kiểm tra xem execution có bị request cancel không.

        Args:
            execution_id: ID của JobExecution cần kiểm tra (string hoặc UUID)
            db: Database session (tùy chọn). Nếu không có, sẽ tạo session mới.

        Returns:
            bool: True nếu execution bị cancel, False nếu không
        """
        should_close_db = False
        if db is None:
            db = SessionLocal()
            should_close_db = True

        try:
            if isinstance(execution_id, str):
                execution_id = UUID(execution_id)

            execution = db.query(JobExecution).filter(JobExecution.id == execution_id).first()
            return execution.status == "cancelled" if execution else False

        except Exception as e:
            logger.error(f"Failed to check cancellation for execution {execution_id}: {e}")
            return False
        finally:
            if should_close_db:
                db.close()
    
    @staticmethod
    def execute_job(job: ScheduledJob, execution_id: Union[str, UUID] = None) -> Dict[str, Any]:
        """Thực thi một scheduled job với đầy đủ tracking và error handling.
        
        Quy trình:
        1. Lấy hoặc tạo JobExecution record
        2. Gọi handler phù hợp dựa trên job.job_type
        3. Cập nhật execution record với kết quả
        4. Cập nhật job.last_run_at
        5. Xử lý errors và cập nhật execution status
        
        Args:
            job: ScheduledJob instance cần thực thi
            execution_id: ID của execution record đã tồn tại (tùy chọn).
                Có thể là string hoặc UUID. Nếu không có, sẽ tạo mới.
        
        Returns:
            Dict[str, Any]: Dictionary chứa kết quả thực thi từ handler:
                - processed: Số lượng items đã xử lý (int)
                - failed: Số lượng items thất bại (int)
                - created: Số lượng items đã tạo (int, optional)
                - updated: Số lượng items đã cập nhật (int, optional)
                - errors: Danh sách error messages (List[str], optional)
                - cancelled: True nếu job bị cancel (bool, optional)
                - message: Thông báo khi job bị cancel (str, optional)
                - Các fields khác tùy theo job type
        
        Raises:
            ValueError: Nếu job_type không được hỗ trợ
            JobCancelledException: Nếu job execution bị cancel (được handle internally)
            Exception: Các exception từ job handlers sẽ được re-raise
        
        Note:
            - Execution record được tạo với status="running" ban đầu
            - Nếu thành công, status được cập nhật thành "completed"
            - Nếu thất bại, status được cập nhật thành "failed" với error_message
            - Nếu bị cancel, status được cập nhật thành "cancelled" với error_message
            - Job.last_run_at được cập nhật sau mỗi lần thực thi
            - Cancellation được check định kỳ trong quá trình execution
        """
        db = SessionLocal()
        execution = None
        
        try:
            # Lấy hoặc tạo bản ghi execution
            if execution_id:
                # Chuyển đổi string sang UUID nếu cần
                if isinstance(execution_id, str):
                    execution_id_uuid = UUID(execution_id)
                else:
                    execution_id_uuid = execution_id
                    
                execution = db.query(JobExecution).filter(JobExecution.id == execution_id_uuid).first()
                if not execution:
                    logger.warning(f"Execution record {execution_id} not found, creating new one")
                    execution = None
                    execution_id = None
                else:
                    execution_id = execution.id
            
            if not execution:
                execution = JobExecution(
                    job_id=job.id,
                    started_at=datetime.now(),
                    status="running"
                )
                db.add(execution)
                db.commit()
                execution_id = execution.id
                logger.info(f"Created execution record: {execution_id}")
            
            # Kiểm tra cancellation trước khi bắt đầu execution
            if execution_id and JobExecutor.is_execution_cancelled(execution_id, db):
                logger.info(f"Execution {execution_id} was cancelled before starting")
                execution = db.query(JobExecution).filter(JobExecution.id == execution_id).first()
                if execution:
                    execution.completed_at = datetime.now()
                    execution.status = "cancelled"
                    execution.error_message = "Job was cancelled before execution started"
                    db.commit()
                return {"cancelled": True, "message": "Job was cancelled before execution started"}
            
            logger.info(f"Executing job: {job.job_name} (type: {job.job_type})")

            # Dispatch tới job handler qua registry — không cần if/elif
            try:
                handler = JOB_REGISTRY.get(job.job_type)
                if not handler:
                    raise ValueError(
                        f"Unknown job type: '{job.job_type}'. "
                        f"Available types: {list(JOB_REGISTRY.keys())}"
                    )
                config = job.config or {}
                result = handler.execute(db, execution_id=execution_id, **config)
                
                # Kiểm tra cancellation sau khi handler hoàn thành
                if execution_id and JobExecutor.is_execution_cancelled(execution_id, db):
                    raise JobCancelledException("Job execution was cancelled during execution")
                
                # Cập nhật bản ghi execution
                if execution_id:
                    execution = db.query(JobExecution).filter(JobExecution.id == execution_id).first()
                    if execution:
                        execution.completed_at = datetime.now()
                        execution.status = "completed"
                        execution.items_processed = result.get('processed', 0)
                        execution.items_failed = result.get('failed', 0)
                        execution.execution_log = result
                        db.commit()
            except JobCancelledException as e:
                logger.info(f"Job execution {execution_id} was cancelled: {e}")
                # Cập nhật bản ghi execution với status cancelled
                if execution_id:
                    execution = db.query(JobExecution).filter(JobExecution.id == execution_id).first()
                    if execution:
                        execution.completed_at = datetime.now()
                        execution.status = "cancelled"
                        execution.error_message = "Job execution was cancelled by user request"
                        # Giữ lại progress đã xử lý nếu có
                        db.commit()
                return {"cancelled": True, "message": str(e)}
            
            # Cập nhật lần chạy cuối của job (lưu ở UTC)
            job_db = db.query(ScheduledJob).filter(ScheduledJob.id == job.id).first()
            if job_db:
                job_db.last_run_at = datetime.now(timezone.utc)
                db.commit()
            
            logger.info(f"Job {job.job_name} completed successfully: {result}")
            return result
            
        except JobCancelledException:
            # Đã xử lý trong try block, không cần xử lý lại ở đây
            raise
        except Exception as e:
            logger.error(f"Job execution failed: {e}", exc_info=True)
            
            # Kiểm tra xem có phải do cancellation không (trường hợp race condition)
            if execution_id and JobExecutor.is_execution_cancelled(execution_id, db):
                logger.info(f"Execution {execution_id} was cancelled, updating status")
                execution = db.query(JobExecution).filter(JobExecution.id == execution_id).first()
                if execution:
                    execution.completed_at = datetime.now()
                    execution.status = "cancelled"
                    execution.error_message = "Job execution was cancelled"
                    db.commit()
                return {"cancelled": True, "message": "Job execution was cancelled"}
            
            # Cập nhật bản ghi execution với lỗi
            if execution_id:
                execution = db.query(JobExecution).filter(JobExecution.id == execution_id).first()
                if execution:
                    execution.completed_at = datetime.now()
                    execution.status = "failed"
                    execution.error_message = str(e)
                    db.commit()
            
            raise
        
        finally:
            db.close()

