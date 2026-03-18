"""Base class cho tất cả Job types.

Mỗi job type kế thừa BaseJob và khai báo:
- name: tên định danh (khớp với job_type trong DB)
- label: tên hiển thị trên UI
- description: mô tả ngắn
- options(): danh sách params job nhận vào
- execute(): logic chính của job
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from sqlalchemy.orm import Session


class JobOption:
    """Mô tả một tham số cấu hình của job.

    Attributes:
        key: Tên param (khớp với key trong job.config dict)
        type: Kiểu dữ liệu hiển thị trên UI:
              "text", "number", "checkbox", "select", "multiselect"
        label: Nhãn hiển thị trên UI
        required: Bắt buộc nhập hay không (mặc định False)
        default: Giá trị mặc định (mặc định None)
        help: Mô tả thêm hiển thị dưới field
        options: Danh sách lựa chọn (chỉ dùng khi type="select" hoặc "multiselect")
        placeholder: Placeholder text cho input
    """

    def __init__(
        self,
        key: str,
        type: str,
        label: str,
        required: bool = False,
        default: Any = None,
        help: str = None,
        options: List[str] = None,
        placeholder: str = None,
    ):
        self.key = key
        self.type = type
        self.label = label
        self.required = required
        self.default = default
        self.help = help
        self.options = options
        self.placeholder = placeholder

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển sang dict để trả về qua API."""
        d = {
            "key": self.key,
            "type": self.type,
            "label": self.label,
            "required": self.required,
            "default": self.default,
        }
        if self.help:
            d["help"] = self.help
        if self.options:
            d["options"] = self.options
        if self.placeholder:
            d["placeholder"] = self.placeholder
        return d


class BaseJob(ABC):
    """Abstract base class cho tất cả job types.

    Subclass phải định nghĩa:
        name (str): Định danh duy nhất, khớp với job_type trong DB.
                    Ví dụ: "redmine_sync"
        label (str): Tên hiển thị trên UI.
                    Ví dụ: "Redmine Sync"
        description (str): Mô tả ngắn về job.

    Subclass phải implement:
        options(): Trả về danh sách JobOption khai báo các params.
        execute(): Logic chính của job.

    Ví dụ:
        class RedmineSyncJob(BaseJob):
            name = "redmine_sync"
            label = "Redmine Sync"
            description = "Đồng bộ issues từ Redmine project"

            def options(self):
                return [
                    JobOption("project_identifier", "text", "Project Identifier", required=True),
                    JobOption("incremental", "checkbox", "Incremental Sync", default=True),
                ]

            def execute(self, db, execution_id=None, **kwargs):
                project_id = kwargs["project_identifier"]
                ...
                return {"processed": 10, "failed": 0}
    """

    name: str = None
    label: str = None
    description: str = ""

    @abstractmethod
    def options(self) -> List[JobOption]:
        """Khai báo danh sách tham số cấu hình của job.

        Returns:
            List[JobOption]: Danh sách các tham số job nhận vào.
                             Được dùng để render form trên Streamlit UI
                             và validate config khi tạo job.
        """
        raise NotImplementedError

    @abstractmethod
    def execute(self, db: Session, execution_id=None, **kwargs) -> Dict[str, Any]:
        """Thực thi logic chính của job.

        Args:
            db: Database session
            execution_id: UUID của JobExecution để check cancellation
            **kwargs: Config của job từ ScheduledJob.config dict

        Returns:
            Dict chứa kết quả:
                - processed (int): Số items đã xử lý
                - failed (int): Số items thất bại
                - errors (List[str]): Danh sách lỗi
                - Các fields khác tuỳ job type
        """
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """Chuyển metadata của job sang dict để trả về qua API."""
        return {
            "name": self.name,
            "label": self.label,
            "description": self.description,
            "options": [opt.to_dict() for opt in self.options()],
        }

    @classmethod
    def run_cli(cls) -> None:
        """Chạy job từ command line.

        Parse args từ sys.argv dựa trên options() của job, tạo DB session,
        rồi gọi execute(). Kết quả in ra stdout dạng JSON.

        Ví dụ:
            python -m app.jobs.redmine_sync_job --project_identifier=myproject
            python -m app.jobs.chunk_embedding_job --limit=200 --batch_size=32
            python -m app.jobs.source_check_job --help
        """
        import argparse
        import json
        import sys

        job = cls()
        opts = job.options()

        parser = argparse.ArgumentParser(
            prog=f"python -m app.jobs.{cls.__module__.split('.')[-1]}",
            description=f"{job.label}: {job.description}",
        )

        # Build argparse args từ options()
        _BOOL_TRUE = {"true", "1", "yes"}
        for opt in opts:
            kwargs: Dict[str, Any] = {
                "dest": opt.key.replace(".", "_"),   # "filters.status" → "filters_status"
                "help": opt.help or "",
                "default": opt.default,
                "required": False,                    # CLI luôn optional (có default)
            }
            if opt.type == "checkbox":
                kwargs["type"] = lambda v: v.lower() in _BOOL_TRUE
                kwargs["metavar"] = "true|false"
            elif opt.type == "number":
                kwargs["type"] = int
            elif opt.type in ("multiselect",):
                kwargs["nargs"] = "*"
            else:
                kwargs["type"] = str

            parser.add_argument(f"--{opt.key.replace('.', '_')}", **kwargs)

        args = parser.parse_args()

        # Build kwargs cho execute() — map lại "filters_status" → "filters.status"
        key_map = {opt.key.replace(".", "_"): opt.key for opt in opts}
        config = {}
        for dest_key, value in vars(args).items():
            original_key = key_map.get(dest_key, dest_key)
            config[original_key] = value

        # Setup DB session and logging
        from app.database import SessionLocal
        from app.logging_config import setup_logging
        setup_logging()

        cli_logger = logging.getLogger(cls.__module__)

        db = SessionLocal()
        try:
            cli_logger.info(f"Running {job.label} with config: {json.dumps(config, default=str, ensure_ascii=False)}")
            result = job.execute(db, execution_id=None, **config)
            cli_logger.info(f"Completed {job.label}: {json.dumps(result, default=str, ensure_ascii=False)}")
            sys.exit(0)
        except KeyboardInterrupt:
            cli_logger.warning(f"{job.label} interrupted by user")
            sys.exit(1)
        except Exception as e:
            cli_logger.error(f"{job.label} failed: {e}", exc_info=True)
            sys.exit(2)
        finally:
            db.close()
