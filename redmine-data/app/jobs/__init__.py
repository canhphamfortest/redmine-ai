"""Job system - mỗi job type là một file độc lập kế thừa BaseJob."""
from app.jobs.base_job import BaseJob, JobOption
from app.jobs.registry import JOB_REGISTRY, discover_jobs

__all__ = ["BaseJob", "JobOption", "JOB_REGISTRY", "discover_jobs"]
