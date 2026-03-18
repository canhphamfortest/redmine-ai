"""Base class cho tất cả Job types.

Mỗi job type kế thừa BaseJob và khai báo:
- name: tên định danh (khớp với job_type trong DB)
- label: tên hiển thị trên UI
- description: mô tả ngắn
- options(): danh sách params job nhận vào
- execute(): logic chính của job
"""
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
