"""Registry tự động discover và quản lý các Job types.

Khi import module này, tất cả job files trong app/jobs/ sẽ được
tự động load và đăng ký vào JOB_REGISTRY.

Thêm job mới chỉ cần tạo file *_job.py trong app/jobs/ kế thừa BaseJob.
"""
import importlib
import logging
import pkgutil
from typing import Dict

logger = logging.getLogger(__name__)


def discover_jobs(package_name: str = "app.jobs") -> Dict[str, "BaseJob"]:
    """Tự động tìm và load tất cả BaseJob subclasses trong package.

    Scan tất cả modules trong package, tìm các class kế thừa BaseJob
    (có thuộc tính `name`), và đăng ký vào registry.

    Args:
        package_name: Tên package chứa các job files (mặc định: "app.jobs")

    Returns:
        Dict[str, BaseJob]: Map từ job.name → job instance
                            Ví dụ: {"redmine_sync": RedmineSyncJob()}
    """
    from app.jobs.base_job import BaseJob

    registry: Dict[str, BaseJob] = {}

    try:
        package = importlib.import_module(package_name)
    except ImportError as e:
        logger.exception(f"Cannot import package {package_name}: {e}")
        return registry

    package_path = getattr(package, "__path__", [])

    for finder, module_name, is_pkg in pkgutil.iter_modules(package_path):
        # Chỉ load file *_job.py, bỏ qua base_job.py và registry.py
        if not module_name.endswith("_job"):
            continue

        full_module_name = f"{package_name}.{module_name}"
        try:
            module = importlib.import_module(full_module_name)
        except Exception as e:
            logger.exception(f"Failed to import job module {full_module_name}: {e}")
            continue

        # Tìm tất cả BaseJob subclasses trong module
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            try:
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BaseJob)
                    and attr is not BaseJob
                    and attr.name is not None
                ):
                    instance = attr()
                    job_name = instance.name

                    # Detect duplicate: same name already registered by a
                    # different class (re-exports or copy-paste errors).
                    if job_name in registry:
                        existing = registry[job_name]
                        existing_cls = type(existing)
                        if existing_cls is not attr:
                            # Different class — surface the conflict clearly
                            logger.error(
                                f"Duplicate job name '{job_name}': "
                                f"already registered as {existing_cls.__module__}.{existing_cls.__qualname__} "
                                f"(from a previous module), "
                                f"skipping {attr.__module__}.{attr.__qualname__} "
                                f"(attr '{attr_name}' in {full_module_name}). "
                                f"Rename one of the job classes or change its `name` attribute."
                            )
                        else:
                            # Same class seen again via re-export — harmless, just skip
                            logger.debug(
                                f"Job '{job_name}' ({attr.__qualname__}) already registered, skipping re-export"
                            )
                        continue  # Never silently overwrite

                    registry[job_name] = instance
                    logger.debug(f"Registered job: {job_name} ({attr.__module__}.{attr.__qualname__})")
            except Exception as e:
                logger.warning(f"Failed to register {attr_name} from {full_module_name}: {e}")

    logger.info(f"Discovered {len(registry)} job types: {list(registry.keys())}")
    return registry


# Registry singleton — được khởi tạo khi module được import lần đầu
JOB_REGISTRY: Dict[str, "BaseJob"] = discover_jobs()
