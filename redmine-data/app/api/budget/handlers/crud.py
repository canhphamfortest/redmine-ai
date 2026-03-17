"""CRUD handlers cho Budget Config API."""
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.database import get_db
from app.models import BudgetConfig
from app.api.budget.schemas import (
    BudgetConfigResponse,
    BudgetConfigCreate,
    BudgetConfigUpdate
)

logger = logging.getLogger(__name__)


async def list_budget_configs(
    active_only: bool = False,
    provider: str = None,
    db: Session = Depends(get_db)
) -> List[BudgetConfigResponse]:
    """Liệt kê tất cả budget configs.
    
    Args:
        active_only: Chỉ lấy configs có is_active=True
        provider: Filter theo provider (optional)
        db: Database session
    
    Returns:
        List[BudgetConfigResponse]: Danh sách budget configs
    """
    try:
        query = db.query(BudgetConfig)
        
        if active_only:
            query = query.filter(BudgetConfig.is_active == True)
        
        if provider:
            query = query.filter(BudgetConfig.provider == provider)
        
        configs = query.all()
        
        return [
            BudgetConfigResponse(
                id=str(config.id),
                provider=config.provider,
                budget_amount_usd=config.budget_amount_usd,
                invoice_day=config.invoice_day,
                alert_thresholds=config.alert_thresholds or [],
                is_active=config.is_active,
                created_at=config.created_at.isoformat() if config.created_at else "",
                updated_at=config.updated_at.isoformat() if config.updated_at else ""
            )
            for config in configs
        ]
    except Exception as e:
        logger.error(f"Failed to list budget configs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def get_budget_config(
    config_id: str,
    db: Session = Depends(get_db)
) -> BudgetConfigResponse:
    """Lấy budget config theo ID.
    
    Args:
        config_id: UUID của budget config
        db: Database session
    
    Returns:
        BudgetConfigResponse: Budget config
    
    Raises:
        HTTPException: 404 nếu không tìm thấy
    """
    try:
        config = db.query(BudgetConfig).filter(BudgetConfig.id == UUID(config_id)).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="Budget config not found")
        
        return BudgetConfigResponse(
            id=str(config.id),
            provider=config.provider,
            budget_amount_usd=config.budget_amount_usd,
            invoice_day=config.invoice_day,
            alert_thresholds=config.alert_thresholds or [],
            is_active=config.is_active,
            created_at=config.created_at.isoformat() if config.created_at else "",
            updated_at=config.updated_at.isoformat() if config.updated_at else ""
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get budget config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def create_budget_config(
    config_data: BudgetConfigCreate,
    db: Session = Depends(get_db)
) -> BudgetConfigResponse:
    """Tạo budget config mới.
    
    Args:
        config_data: Budget config data
        db: Database session
    
    Returns:
        BudgetConfigResponse: Budget config đã tạo
    
    Raises:
        HTTPException: 400 nếu provider đã có config
    """
    try:
        # Kiểm tra xem đã có config cho provider này chưa
        existing = db.query(BudgetConfig).filter(
            BudgetConfig.provider == config_data.provider
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Budget config already exists for provider: {config_data.provider}"
            )
        
        # Tạo config mới
        config = BudgetConfig(
            provider=config_data.provider,
            budget_amount_usd=config_data.budget_amount_usd,
            invoice_day=config_data.invoice_day,
            alert_thresholds=config_data.alert_thresholds,
            is_active=config_data.is_active
        )
        
        db.add(config)
        db.commit()
        db.refresh(config)
        
        logger.info(f"Created budget config for provider: {config_data.provider}")
        
        return BudgetConfigResponse(
            id=str(config.id),
            provider=config.provider,
            budget_amount_usd=config.budget_amount_usd,
            invoice_day=config.invoice_day,
            alert_thresholds=config.alert_thresholds or [],
            is_active=config.is_active,
            created_at=config.created_at.isoformat() if config.created_at else "",
            updated_at=config.updated_at.isoformat() if config.updated_at else ""
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create budget config: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def update_budget_config(
    config_id: str,
    config_data: BudgetConfigUpdate,
    db: Session = Depends(get_db)
) -> BudgetConfigResponse:
    """Cập nhật budget config.
    
    Args:
        config_id: UUID của budget config
        config_data: Budget config update data
        db: Database session
    
    Returns:
        BudgetConfigResponse: Budget config đã cập nhật
    
    Raises:
        HTTPException: 404 nếu không tìm thấy
    """
    try:
        config = db.query(BudgetConfig).filter(BudgetConfig.id == UUID(config_id)).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="Budget config not found")
        
        # Cập nhật các fields được cung cấp
        if config_data.budget_amount_usd is not None:
            config.budget_amount_usd = config_data.budget_amount_usd
        if config_data.invoice_day is not None:
            config.invoice_day = config_data.invoice_day
        if config_data.alert_thresholds is not None:
            config.alert_thresholds = config_data.alert_thresholds
        if config_data.is_active is not None:
            config.is_active = config_data.is_active
        
        db.commit()
        db.refresh(config)
        
        logger.info(f"Updated budget config: {config_id}")
        
        return BudgetConfigResponse(
            id=str(config.id),
            provider=config.provider,
            budget_amount_usd=config.budget_amount_usd,
            invoice_day=config.invoice_day,
            alert_thresholds=config.alert_thresholds or [],
            is_active=config.is_active,
            created_at=config.created_at.isoformat() if config.created_at else "",
            updated_at=config.updated_at.isoformat() if config.updated_at else ""
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update budget config: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def delete_budget_config(
    config_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """Xóa budget config.
    
    Args:
        config_id: UUID của budget config
        db: Database session
    
    Returns:
        dict: Success message
    
    Raises:
        HTTPException: 404 nếu không tìm thấy
    """
    try:
        config = db.query(BudgetConfig).filter(BudgetConfig.id == UUID(config_id)).first()
        
        if not config:
            raise HTTPException(status_code=404, detail="Budget config not found")
        
        db.delete(config)
        db.commit()
        
        logger.info(f"Deleted budget config: {config_id}")
        
        return {"message": "Budget config deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete budget config: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
