"""Handlers cho Budget Alerts API."""
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from app.database import get_db
from app.models import BudgetAlert
from app.services.budget import AlertService
from app.api.budget.schemas import BudgetAlertResponse

logger = logging.getLogger(__name__)


async def list_alerts(
    provider: Optional[str] = None,
    unacknowledged_only: bool = False,
    limit: int = 100,
    db: Session = Depends(get_db)
) -> List[BudgetAlertResponse]:
    """Lấy danh sách budget alerts.
    
    Args:
        provider: Filter theo provider (optional)
        unacknowledged_only: Chỉ lấy alerts chưa acknowledge
        limit: Số lượng alerts tối đa
        db: Database session
    
    Returns:
        List[BudgetAlertResponse]: Danh sách alerts
    """
    try:
        query = db.query(BudgetAlert)
        
        if provider:
            query = query.filter(BudgetAlert.provider == provider)
        
        if unacknowledged_only:
            query = query.filter(BudgetAlert.acknowledged_at.is_(None))
        
        alerts = query.order_by(BudgetAlert.sent_at.desc()).limit(limit).all()
        
        return [
            BudgetAlertResponse(
                id=str(alert.id),
                budget_config_id=str(alert.budget_config_id),
                provider=alert.provider,
                billing_cycle_start=alert.billing_cycle_start.isoformat() if alert.billing_cycle_start else "",
                billing_cycle_end=alert.billing_cycle_end.isoformat() if alert.billing_cycle_end else "",
                threshold_percentage=alert.threshold_percentage,
                current_spending_usd=alert.current_spending_usd,
                budget_amount_usd=alert.budget_amount_usd,
                alert_type=alert.alert_type,
                alert_channels=alert.alert_channels or [],
                sent_at=alert.sent_at.isoformat() if alert.sent_at else "",
                acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                created_at=alert.created_at.isoformat() if alert.created_at else ""
            )
            for alert in alerts
        ]
    except Exception as e:
        logger.error(f"Failed to list alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def acknowledge_alert(
    alert_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """Acknowledge một alert.
    
    Args:
        alert_id: UUID của alert
        db: Database session
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException: 404 nếu không tìm thấy alert
    """
    try:
        alert = db.query(BudgetAlert).filter(BudgetAlert.id == UUID(alert_id)).first()
        
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        if alert.acknowledged_at:
            return {"message": "Alert already acknowledged"}
        
        alert.acknowledged_at = datetime.now()
        db.commit()
        
        logger.info(f"Acknowledged alert: {alert_id}")
        
        return {"message": "Alert acknowledged successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
