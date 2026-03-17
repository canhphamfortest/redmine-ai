"""Các handler đồng bộ model mặc định và pricing"""
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings as app_settings
from app.services.openai_config_service import OpenAIConfigService

logger = logging.getLogger(__name__)


async def sync_default_pricing(db: Session = Depends(get_db)):
    """Đồng bộ pricing mặc định từ giá trị hardcoded sang database.
    
    Endpoint này đồng bộ tất cả pricing từ hardcoded PRICING dictionary vào database.
    Mỗi model trong PRICING sẽ được tạo hoặc cập nhật trong database.
    
    Args:
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa message với số lượng config đã sync
    
    Raises:
        HTTPException: HTTP 500 nếu có lỗi trong quá trình sync
    
    Note:
        - Tất cả models trong PRICING được sync với is_active=True
        - Model mặc định được đặt là 'gpt-4o-mini' (nếu chưa có default khác)
        - Config được commit vào database
    """
    try:
        count = OpenAIConfigService.sync_default_pricing(db)
        db.commit()
        return {"message": f"Đã đồng bộ {count} cấu hình pricing mặc định"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def get_default_model(db: Session = Depends(get_db)):
    """Lấy tên model mặc định từ database hoặc config.
    
    Endpoint này trả về model mặc định đang được sử dụng. Kiểm tra database
    trước, nếu không có thì fallback về settings.openai_model.
    
    Args:
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - default_model: Tên model mặc định (str)
            - from_db: True nếu lấy từ database, False nếu từ config (bool)
    
    Raises:
        HTTPException: HTTP 500 nếu có lỗi trong quá trình query
    """
    try:
        config = OpenAIConfigService.get_default_provider_and_model(db)
        return {
            "default_model": config.get("model"),
            "provider": config.get("provider"),
            "from_db": config.get("model") != app_settings.openai_model or config.get("provider") != app_settings.default_llm_provider,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def set_default_model(
    model_name: str,
    provider: str = "openai",
    db: Session = Depends(get_db)
):
    """Đặt một model làm mặc định.
    
    Endpoint này đặt một model cụ thể làm model mặc định. Tất cả các model khác
    sẽ bị bỏ default flag. Model được đặt làm default cũng được đảm bảo is_active=True.
    
    Args:
        model_name: Tên model cần đặt làm mặc định (string)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa:
            - message: Thông báo thành công (str)
            - default_model: Tên model đã được đặt làm mặc định (str)
    
    Raises:
        HTTPException:
            - HTTP 404 nếu model không tồn tại trong database
            - HTTP 500 nếu có lỗi trong quá trình cập nhật
    
    Note:
        - Chỉ có một model có thể là default tại một thời điểm
        - Model được đặt làm default cũng được set is_active=True
        - Config được commit vào database
    """
    try:
        success = OpenAIConfigService.set_default_model(model_name, db, provider=provider)
        if not success:
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
        
        db.commit()
        return {
            "message": f"Model {model_name} set as default",
            "default_model": model_name,
            "provider": provider,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

