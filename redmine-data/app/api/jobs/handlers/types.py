"""Handler trả về danh sách job types có sẵn."""
import logging
from fastapi import Depends, HTTPException
from app.auth import get_current_user

logger = logging.getLogger(__name__)


async def list_job_types(current_user=Depends(get_current_user)):
    """Trả về danh sách tất cả job types đã đăng ký cùng options của từng loại.

    Endpoint này được Streamlit UI dùng để render form tạo job động —
    không cần hardcode từng job type trên frontend.

    Returns:
        dict: {"job_types": [{"name", "label", "description", "options": [...]}]}

    Raises:
        HTTPException: HTTP 500 nếu có lỗi khi load registry
    """
    try:
        from app.jobs.registry import JOB_REGISTRY

        return {
            "job_types": [job.to_dict() for job in JOB_REGISTRY.values()]
        }

    except Exception as e:
        logger.exception("Failed to list job types")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error while loading job types"
        ) from e
