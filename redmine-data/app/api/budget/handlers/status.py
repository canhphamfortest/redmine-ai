"""Handlers cho Budget Status API."""
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.budget import BudgetService
from app.api.budget.schemas import BudgetStatusListResponse, BudgetStatusResponse

logger = logging.getLogger(__name__)


async def get_budget_status(
    db: Session = Depends(get_db)
) -> BudgetStatusListResponse:
    """Lấy trạng thái budget cho tất cả providers.
    
    Args:
        db: Database session
    
    Returns:
        BudgetStatusListResponse: Danh sách budget status
    """
    try:
        status_data = BudgetService.get_budget_status(db=db)
        
        statuses = [
            BudgetStatusResponse(**status)
            for status in status_data['statuses']
        ]
        
        return BudgetStatusListResponse(
            statuses=statuses,
            total_providers=status_data['total_providers']
        )
    except Exception as e:
        logger.error(f"Failed to get budget status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def get_budget_status_by_provider(
    provider: str,
    db: Session = Depends(get_db)
) -> BudgetStatusResponse:
    """Lấy trạng thái budget cho provider cụ thể.
    
    Args:
        provider: Provider name (openai, google, anthropic, groq)
        db: Database session
    
    Returns:
        BudgetStatusResponse: Budget status cho provider
    
    Raises:
        HTTPException: 404 nếu không tìm thấy budget config cho provider
    """
    try:
        status_data = BudgetService.get_budget_status(provider=provider, db=db)
        
        if not status_data['statuses']:
            raise HTTPException(
                status_code=404,
                detail=f"No budget config found for provider: {provider}"
            )
        
        # Lấy status đầu tiên (chỉ có một config per provider)
        status = status_data['statuses'][0]
        
        return BudgetStatusResponse(**status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get budget status for provider {provider}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
