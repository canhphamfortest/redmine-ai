"""Dịch vụ Job Scheduler nhẹ.

Scheduler này được thiết kế để nhẹ (~200MB Docker image) bằng cách:
1. KHÔNG import các dependency ML nặng (torch, transformers, sentence-transformers)
2. Gọi Backend API để thực thi jobs thay vì chạy trực tiếp

Điều này cho phép chạy scheduler trong một container nhỏ riêng biệt trong khi 
các tính toán nặng được thực hiện bởi dịch vụ backend.

Module này cung cấp JobSchedulerService class để:
- Schedule jobs: Schedule các jobs dựa trên cron expressions
- Job loading: Load jobs từ database và schedule chúng
- Job execution: Trigger job execution qua backend API
- Job reloading: Tự động reload jobs khi có thay đổi
- Event handling: Xử lý job execution events và cập nhật next_run_at

Sử dụng APScheduler để quản lý scheduling và httpx để gọi backend API.
"""

import logging
import time
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from app.schedulers.budget_checker import check_budget_thresholds_job
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import SessionLocal
from app.models import ScheduledJob, JobExecution
from app.config import settings

# Import logging config để ghi log ra file
try:
    from app.logging_config import setup_logging
    setup_logging(service_name="scheduler", level="INFO")
    logger = logging.getLogger(__name__)
except ImportError:
    # Fallback nếu logging_config chưa có
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)


class JobSchedulerService:
    """
    Dịch vụ APScheduler nhẹ gọi Backend API để thực thi job.
    
    Dịch vụ này:
    - Quản lý cron schedules trong memory
    - Poll database để phát hiện thay đổi job
    - Kích hoạt thực thi job qua Backend API (không chạy local)
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=settings.scheduler_timezone)
        self.scheduler.add_listener(self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)
        self.db = SessionLocal()
        self.backend_url = settings.backend_api_url.rstrip('/')
        
        # Local timezone object để tính toán cron
        self.local_tz = ZoneInfo(settings.scheduler_timezone)
        
        # HTTP client với connection pooling
        self.http_client = httpx.Client(
            base_url=self.backend_url,
            timeout=httpx.Timeout(300.0, connect=10.0),  # Timeout 5 phút cho jobs dài
            follow_redirects=True
        )
        
        # Lưu cron_expression cho các jobs đang sử dụng DateTrigger
        # Key: job_id (string), Value: cron_expression (string)
        self._date_trigger_jobs = {}
        
    def start(self):
        """Khởi động scheduler và bắt đầu quản lý jobs.
        
        Quy trình:
        1. Đợi backend API sẵn sàng
        2. Khởi động APScheduler
        3. Tải jobs từ database
        4. Chạy loop kiểm tra và reload jobs mỗi phút
        
        Note:
            - Scheduler chạy trong background thread
            - Jobs được reload mỗi 60 giây để phát hiện thay đổi
            - Có thể dừng bằng KeyboardInterrupt (Ctrl+C)
        """
        logger.info("Starting Lightweight Job Scheduler...")
        logger.info(f"Backend API URL: {self.backend_url}")
        
        # Đợi backend sẵn sàng
        self._wait_for_backend()
        
        # Khởi động scheduler trước
        self.scheduler.start()
        logger.info("Job Scheduler started successfully")

        # Chạy kiểm tra budget mỗi giờ một lần
        self.scheduler.add_job(
            check_budget_thresholds_job,
            # trigger=CronTrigger.from_crontab("25 * * * *"),
            trigger=CronTrigger.from_crontab("*/5 * * * *"),  # Test mỗi 5 phút
            id="system_budget_checker",
            name="System Budget Threshold Checker",
            replace_existing=True
        )
        
        logger.info("System Budget Checker job added to scheduler")
        
        # Tải jobs từ database sau khi scheduler đã khởi động
        self._load_jobs()
        
        # Tiếp tục chạy
        try:
            while True:
                time.sleep(60)  # Kiểm tra mỗi phút
                self._reload_jobs()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Shutting down Job Scheduler...")
            self.scheduler.shutdown()
            self.http_client.close()
    
    def _wait_for_backend(self, max_retries: int = 30, retry_interval: int = 10):
        """Đợi backend API sẵn sàng trước khi khởi động scheduler.
        
        Hàm này kiểm tra endpoint /health của backend API cho đến khi
        backend sẵn sàng hoặc hết số lần retry.
        
        Args:
            max_retries: Số lần retry tối đa (mặc định: 30)
            retry_interval: Khoảng thời gian giữa các lần retry tính bằng giây (mặc định: 10)
        
        Note:
            - Tổng thời gian chờ tối đa = max_retries * retry_interval (mặc định: 5 phút)
            - Nếu backend không sẵn sàng sau max_retries, sẽ tiếp tục với warning
            - Sử dụng /health endpoint để kiểm tra
        """
        logger.info("Waiting for backend API to be ready...")
        
        for i in range(max_retries):
            try:
                response = self.http_client.get("/health")
                if response.status_code == 200:
                    logger.info("Backend API is ready")
                    return
            except Exception as e:
                logger.debug(f"Backend not ready yet: {e}")
            
            logger.info(f"Waiting for backend... ({i + 1}/{max_retries})")
            time.sleep(retry_interval)
        
        logger.warning("Backend not ready after waiting, proceeding anyway...")
    
    def _load_jobs(self):
        """Tải tất cả các jobs đang hoạt động từ database vào scheduler.
        
        Hàm này query database để lấy tất cả jobs có is_active=True,
        sau đó thêm từng job vào scheduler. Nếu có lỗi khi thêm một job,
        sẽ log error nhưng tiếp tục với các jobs khác.
        
        Note:
            - Tạo database session mới trước khi query
            - Chỉ load jobs có is_active=True
            - Mỗi job được thêm bằng _add_job()
            - Log số lượng jobs đã load thành công
        """
        try:
            # Làm mới database session
            self.db.close()
            self.db = SessionLocal()
            
            jobs = self.db.query(ScheduledJob).filter(ScheduledJob.is_active == True).all()
            
            added_count = 0
            for job in jobs:
                try:
                    self._add_job(job)
                    added_count += 1
                except Exception as e:
                    logger.error(f"Failed to add job {job.id} ({job.job_name}): {e}")
            
            logger.info(f"Loaded {added_count}/{len(jobs)} active jobs")
            
        except Exception as e:
            logger.error(f"Failed to load jobs: {e}", exc_info=True)
    
    def _reload_jobs(self):
        """Tải lại jobs định kỳ để phát hiện thay đổi từ database.
        
        Hàm này so sánh jobs trong scheduler với jobs trong database:
        1. Xóa các jobs không còn active hoặc không tồn tại trong database
        2. Thêm hoặc cập nhật các jobs từ database
        
        Quy trình:
        - Lấy danh sách job IDs đang được schedule
        - Query database để lấy jobs active
        - So sánh và xóa jobs không còn trong database
        - Thêm/cập nhật jobs từ database
        
        Note:
            - Được gọi định kỳ mỗi 60 giây trong start() loop
            - Tạo database session mới cho mỗi lần reload
            - Jobs được replace nếu đã tồn tại (replace_existing=True)
            - System jobs (như system_budget_checker) được bảo vệ khỏi việc xóa
        """
        try:
            # Danh sách system jobs không được xóa
            SYSTEM_JOBS = {"system_budget_checker"}
            
            # Lấy các job IDs đang được lên lịch (đảm bảo chúng là strings)
            scheduled_job_ids = {str(job.id) for job in self.scheduler.get_jobs()}
            
            # Lấy các jobs đang hoạt động từ database
            self.db.close()
            self.db = SessionLocal()
            db_jobs = self.db.query(ScheduledJob).filter(ScheduledJob.is_active == True).all()
            db_job_ids = {str(job.id) for job in db_jobs}
            
            # Xóa các jobs không còn hoạt động hoặc không tồn tại
            # KHÔNG xóa system jobs
            jobs_to_remove = (scheduled_job_ids - db_job_ids) - SYSTEM_JOBS
            for job_id in jobs_to_remove:
                try:
                    self.scheduler.remove_job(job_id)
                    # Xóa khỏi _date_trigger_jobs nếu có
                    if job_id in self._date_trigger_jobs:
                        del self._date_trigger_jobs[job_id]
                    logger.info(f"Removed inactive job: {job_id}")
                except Exception as e:
                    logger.warning(f"Failed to remove job {job_id}: {e}")
            
            # Thêm hoặc cập nhật jobs từ database
            for job in db_jobs:
                try:
                    self._add_job(job)
                except Exception as e:
                    logger.error(f"Failed to reload job {job.id}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to reload jobs: {e}", exc_info=True)
    
    def _add_job(self, job: ScheduledJob):
        """Thêm một job vào APScheduler với cron trigger.
        
        Hàm này parse cron expression, tạo trigger, và thêm job vào scheduler.
        Nếu job đã tồn tại, sẽ remove trước rồi thêm lại.
        
        Args:
            job: ScheduledJob instance cần thêm vào scheduler
        
        Note:
            - Sử dụng CronTrigger.from_crontab() để parse cron expression
            - Nếu next_run_at được set trong database, sẽ sử dụng giá trị đó thay vì tính từ cron
            - Tất cả jobs gọi _execute_job_via_api() để thực thi qua Backend API
            - Misfire grace time = 300 giây (5 phút)
            - Job ID là string của job.id
            - Log next_run_time sau khi thêm thành công
        """
        try:
            # Kiểm tra xem job đã tồn tại trong scheduler chưa
            existing_job = self.scheduler.get_job(str(job.id))
            if existing_job:
                logger.debug(f"Job {job.job_name} already exists in scheduler, removing it first")
                self.scheduler.remove_job(str(job.id))
                # Xóa khỏi _date_trigger_jobs nếu có
                if str(job.id) in self._date_trigger_jobs:
                    del self._date_trigger_jobs[str(job.id)]
            
            # Kiểm tra xem có next_run_at được set trong database không
            # Nếu có và nó khác với thời gian tính từ cron, sử dụng next_run_at từ database
            trigger = None
            use_date_trigger = False
            
            # Sử dụng CronTrigger với local timezone để parse cron expression
            # Cron expression được hiểu theo local timezone (ví dụ: 30 10 * * * = 10:30 local time)
            trigger = CronTrigger.from_crontab(job.cron_expression, timezone=settings.scheduler_timezone)
            
            # Nếu có next_run_at trong DB và nó còn trong tương lai, sử dụng DateTrigger
            if job.next_run_at:
                # next_run_at trong DB là UTC, so sánh với UTC now
                now_utc = datetime.now(timezone.utc)
                
                if job.next_run_at > now_utc:
                    # Sử dụng next_run_at từ database cho lần chạy đầu tiên
                    logger.debug(f"Using next_run_at from database ({job.next_run_at}) for job {job.job_name}")
                    trigger = DateTrigger(run_date=job.next_run_at)
                    use_date_trigger = True
            
            # Lưu cron_expression nếu job đang sử dụng DateTrigger
            if use_date_trigger:
                self._date_trigger_jobs[str(job.id)] = job.cron_expression
            
            # Thêm job vào scheduler - tất cả jobs sử dụng cùng phương thức thực thi
            # gọi Backend API
            scheduled_job = self.scheduler.add_job(
                self._execute_job_via_api,
                trigger=trigger,
                id=str(job.id),
                name=job.job_name,
                args=[str(job.id), job.job_name, job.job_type],
                misfire_grace_time=300,  # 5 phút
                replace_existing=True
            )
            
            next_run = scheduled_job.next_run_time
            logger.info(f"Added job: {job.job_name} ({job.id}), type: {job.job_type}, next run: {next_run}")
            
        except Exception as e:
            logger.error(f"Failed to add job {job.id}: {e}", exc_info=True)
    
    def _execute_job_via_api(self, job_id: str, job_name: str, job_type: str):
        """Thực thi job bằng cách gọi Backend API endpoint.
        
        Đây là điểm khác biệt chính của lightweight scheduler - không import
        và chạy các dịch vụ nặng (ML models, embeddings) ở đây. Thay vào đó,
        gọi Backend API endpoint /api/jobs/{job_id}/run để thực thi job.
        
        Quy trình:
        1. Gọi POST /api/jobs/{job_id}/run
        2. Đợi response từ backend
        3. Cập nhật next_run_at trong database
        4. Nếu job đang sử dụng DateTrigger, reschedule với CronTrigger
        5. Log kết quả
        
        Args:
            job_id: ID của job cần thực thi (string)
            job_name: Tên của job (string)
            job_type: Loại job (redmine_sync, git_sync, source_check) (string)
        
        Note:
            - Sử dụng httpx client với timeout 5 phút
            - Backend API sẽ tạo execution record và thực thi job
            - Nếu API call thất bại, sẽ log error nhưng không raise exception
            - next_run_at được cập nhật sau khi job được trigger
            - Nếu job đang sử dụng DateTrigger, sẽ được reschedule với CronTrigger sau lần chạy đầu
        """
        logger.info(f"Triggering job via API: {job_name} (id: {job_id}, type: {job_type})")
        
        try:
            # Gọi Backend API để thực thi job
            response = self.http_client.post(
                f"/api/jobs/{job_id}/run",
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                execution_id = result.get('execution_id')
                logger.info(f"Job {job_name} triggered successfully, execution_id: {execution_id}")
                
                # Cập nhật next_run_at trong database
                self._update_next_run_at(job_id)
                
                # Nếu job đang sử dụng DateTrigger, reschedule với CronTrigger
                if job_id in self._date_trigger_jobs:
                    cron_expression = self._date_trigger_jobs.pop(job_id)  # Xóa khỏi dict sau khi dùng
                    try:
                        cron_trigger = CronTrigger.from_crontab(cron_expression, timezone=settings.scheduler_timezone)
                        self.scheduler.reschedule_job(
                            job_id,
                            trigger=cron_trigger
                        )
                        logger.info(f"Rescheduled job {job_name} with CronTrigger for subsequent runs")
                    except Exception as e:
                        logger.error(f"Failed to reschedule job {job_name} with CronTrigger: {e}")
                
                return result
            else:
                logger.error(f"Failed to trigger job {job_name}: HTTP {response.status_code} - {response.text}")
                return {"error": f"HTTP {response.status_code}", "detail": response.text}
                
        except httpx.TimeoutException:
            logger.error(f"Timeout triggering job {job_name}")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"Failed to trigger job {job_name}: {e}", exc_info=True)
            return {"error": str(e)}
    
    def _update_next_run_at(self, job_id: str):
        """Cập nhật next_run_at và last_run_at cho job trong database.
        
        Hàm này tính toán thời gian chạy tiếp theo dựa trên cron expression
        và cập nhật vào database. Cron expression được hiểu theo local timezone,
        sau đó được convert sang UTC để lưu vào database.
        
        Args:
            job_id: ID của job cần cập nhật (string)
        
        Note:
            - Cron expression được parse với local timezone (ví dụ: 30 10 * * * = 10:30 local)
            - Tính toán next_run trong local timezone, sau đó convert sang UTC để lưu DB
            - last_run_at được lưu ở UTC
            - Tạo database session mới và đóng sau khi xong
            - Nếu job không tồn tại, sẽ return sớm
        """
        db = SessionLocal()
        try:
            from croniter import croniter
            
            job = db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()
            if not job:
                return
            
            # Tính toán thời gian chạy tiếp theo từ bây giờ
            # Cron expression được hiểu theo local timezone
            now_local = datetime.now(self.local_tz)
            cron = croniter(job.cron_expression, now_local)
            next_run_local = cron.get_next(datetime)
            
            # Đảm bảo next_run_local có local timezone
            if next_run_local.tzinfo is None:
                next_run_local = next_run_local.replace(tzinfo=self.local_tz)
            
            # Convert sang UTC để lưu vào database
            next_run_utc = next_run_local.astimezone(timezone.utc)
            now_utc = datetime.now(timezone.utc)
            
            job.next_run_at = next_run_utc
            job.last_run_at = now_utc
            db.commit()
            
            logger.debug(f"Updated next_run_at for job {job.job_name}: {next_run_utc} (UTC) = {next_run_local} (local)")
            
        except Exception as e:
            logger.error(f"Failed to update next_run_at for job {job_id}: {e}")
            db.rollback()
        finally:
            db.close()
    
    def _job_listener(self, event):
        """Event listener cho các sự kiện job execution từ APScheduler.
        
        Hàm này được gọi tự động bởi APScheduler khi job được thực thi
        (EVENT_JOB_EXECUTED) hoặc có lỗi (EVENT_JOB_ERROR).
        
        Args:
            event: APScheduler event object chứa thông tin về job execution
        
        Note:
            - Log error nếu có exception
            - Log success với scheduled_run_time nếu không có lỗi
            - Được đăng ký trong __init__ với EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        """
        if event.exception:
            logger.error(f"Job {event.job_id} failed with exception: {event.exception}", exc_info=event.exception)
        else:
            logger.info(f"Job {event.job_id} executed successfully at {event.scheduled_run_time}")


def main():
    """Điểm vào chính của scheduler service.
    
    Hàm này khởi tạo JobSchedulerService và bắt đầu scheduler.
    Scheduler sẽ chạy cho đến khi nhận được KeyboardInterrupt hoặc SystemExit.
    
    Note:
        - Được gọi khi chạy script trực tiếp (python -m app.schedulers.job_scheduler)
        - Scheduler chạy trong main thread và block cho đến khi dừng
    """
    service = JobSchedulerService()
    service.start()


if __name__ == "__main__":
    main()
