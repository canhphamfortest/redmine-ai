"""Handler cho budget check endpoint (used by scheduler)."""
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schedulers.budget_checker import check_budget_thresholds_job

logger = logging.getLogger(__name__)


async def check_budget_thresholds_endpoint(
    db: Session = Depends(get_db)
) -> dict:
    """Endpoint để trigger budget threshold check (dùng bởi scheduler).
    
    Args:
        db: Database session
    
    Returns:
        dict: Result message
    """
    try:
        check_budget_thresholds_job()
        return {
            "message": "Budget threshold check completed",
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Budget threshold check failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
