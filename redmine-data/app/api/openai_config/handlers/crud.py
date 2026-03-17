"""Các handler CRUD cho API LLM Config (hỗ trợ OpenAI, Google, Anthropic, Groq)"""
import logging
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.services.openai_config_service import OpenAIConfigService
from app.api.openai_config.schemas import OpenAIConfigResponse, OpenAIConfigCreate, OpenAIConfigUpdate

logger = logging.getLogger(__name__)


async def list_configs(
    active_only: bool = False,
    provider: str = None,
    db: Session = Depends(get_db)
):
    """Liệt kê tất cả các config LLM với filter tùy chọn.
    
    Endpoint này trả về danh sách tất cả LLM configs trong database.
    Có thể filter để chỉ lấy các configs đang active.
    
    Args:
        active_only: Chỉ lấy configs có is_active=True (mặc định: False)
        db: Database session (dependency injection)
    
    Returns:
        List[OpenAIConfigResponse]: Danh sách configs, mỗi config chứa:
            - id: UUID của config (str)
            - model_name: Tên model (str)
            - input_price_per_1m: Giá input tokens cho mỗi 1M tokens (float)
            - output_price_per_1m: Giá output tokens cho mỗi 1M tokens (float)
            - is_active: Trạng thái active (bool)
            - is_default: Có phải model mặc định không (bool)
            - description: Mô tả config (str, optional)
            - created_at: Thời gian tạo (str, ISO format)
            - updated_at: Thời gian cập nhật (str, ISO format)
    
    Raises:
        HTTPException: HTTP 500 nếu có lỗi trong quá trình query
    """
    try:
        if active_only:
            configs = OpenAIConfigService.get_active_configs(db, provider=provider)
        else:
            configs = OpenAIConfigService.get_all_configs(db, provider=provider)
        
        return [
            OpenAIConfigResponse(
                id=str(config.id),
                model_name=config.model_name,
                input_price_per_1m=config.input_price_per_1m,
                output_price_per_1m=config.output_price_per_1m,
                is_active=config.is_active,
                is_default=config.is_default,
                description=config.description,
                provider=config.provider,
                api_key=None,
                base_url=config.base_url,
                created_at=config.created_at.isoformat() if config.created_at else "",
                updated_at=config.updated_at.isoformat() if config.updated_at else ""
            )
            for config in configs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def get_config(
    model_name: str,
    db: Session = Depends(get_db)
):
    """Lấy config cho một model cụ thể.
    
    Args:
        model_name: Tên model cần lấy config (string)
        db: Database session (dependency injection)
    
    Returns:
        OpenAIConfigResponse: Config object chứa thông tin đầy đủ về model
    
    Raises:
        HTTPException:
            - HTTP 404 nếu config không tồn tại
            - HTTP 500 nếu có lỗi trong quá trình query
    """
    try:
        config = OpenAIConfigService.get_config_by_model(model_name, db)
        if not config:
            raise HTTPException(status_code=404, detail=f"Config for model {model_name} not found")
        
        return OpenAIConfigResponse(
            id=str(config.id),
            model_name=config.model_name,
            input_price_per_1m=config.input_price_per_1m,
            output_price_per_1m=config.output_price_per_1m,
            is_active=config.is_active,
            is_default=config.is_default,
            description=config.description,
            provider=config.provider,
            api_key=None,
            base_url=config.base_url,
            created_at=config.created_at.isoformat() if config.created_at else "",
            updated_at=config.updated_at.isoformat() if config.updated_at else ""
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def create_config(
    config_data: OpenAIConfigCreate,
    db: Session = Depends(get_db)
):
    """Tạo hoặc cập nhật config OpenAI.
    
    Endpoint này tạo config mới nếu chưa tồn tại, hoặc cập nhật config hiện có
    nếu đã tồn tại (dựa trên model_name).
    
    Args:
        config_data: OpenAIConfigCreate schema chứa:
            - model_name: Tên model (str)
            - input_price_per_1m: Giá input tokens (float)
            - output_price_per_1m: Giá output tokens (float)
            - is_active: Trạng thái active (bool)
            - description: Mô tả config (str, optional)
        db: Database session (dependency injection)
    
    Returns:
        OpenAIConfigResponse: Config object đã được tạo hoặc cập nhật
    
    Raises:
        HTTPException: HTTP 500 nếu có lỗi trong quá trình tạo/cập nhật
    
    Note:
        - Nếu config đã tồn tại, sẽ được cập nhật với giá trị mới
        - Config được commit vào database
    """
    try:
        config = OpenAIConfigService.create_or_update_config(
            model_name=config_data.model_name,
            input_price_per_1m=config_data.input_price_per_1m,
            output_price_per_1m=config_data.output_price_per_1m,
            is_active=config_data.is_active,
            description=config_data.description,
            db=db,
            provider=config_data.provider,
            api_key=config_data.api_key,
            base_url=config_data.base_url,
        )
        db.commit()
        
        return OpenAIConfigResponse(
            id=str(config.id),
            model_name=config.model_name,
            input_price_per_1m=config.input_price_per_1m,
            output_price_per_1m=config.output_price_per_1m,
            is_active=config.is_active,
            is_default=config.is_default,
            description=config.description,
            provider=config.provider,
            api_key=None,
            base_url=config.base_url,
            created_at=config.created_at.isoformat() if config.created_at else "",
            updated_at=config.updated_at.isoformat() if config.updated_at else ""
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def update_config(
    model_name: str,
    config_data: OpenAIConfigUpdate,
    db: Session = Depends(get_db)
):
    """Cập nhật config OpenAI.
    
    Endpoint này cập nhật các trường của config hiện có. Chỉ các trường được
    cung cấp trong config_data mới được cập nhật (partial update).
    
    Args:
        model_name: Tên model cần cập nhật config (string)
        config_data: OpenAIConfigUpdate schema chứa các trường cần cập nhật:
            - input_price_per_1m: Giá input tokens mới (float, optional)
            - output_price_per_1m: Giá output tokens mới (float, optional)
            - is_active: Trạng thái active mới (bool, optional)
            - description: Mô tả mới (str, optional)
        db: Database session (dependency injection)
    
    Returns:
        OpenAIConfigResponse: Config object đã được cập nhật
    
    Raises:
        HTTPException:
            - HTTP 404 nếu config không tồn tại
            - HTTP 500 nếu có lỗi trong quá trình cập nhật
    
    Note:
        - Chỉ các trường được cung cấp mới được cập nhật
        - Config được commit vào database
    """
    try:
        existing_config = OpenAIConfigService.get_config_by_model(model_name, db)
        if not existing_config:
            raise HTTPException(status_code=404, detail=f"Config for model {model_name} not found")
        
        # Cập nhật các trường nếu được cung cấp
        if config_data.input_price_per_1m is not None:
            existing_config.input_price_per_1m = config_data.input_price_per_1m
        if config_data.output_price_per_1m is not None:
            existing_config.output_price_per_1m = config_data.output_price_per_1m
        if config_data.is_active is not None:
            existing_config.is_active = config_data.is_active
        if config_data.description is not None:
            existing_config.description = config_data.description
        if config_data.provider is not None:
            existing_config.provider = config_data.provider
        if config_data.api_key is not None:
            existing_config.api_key = config_data.api_key
        if config_data.base_url is not None:
            existing_config.base_url = config_data.base_url
        
        db.commit()
        db.refresh(existing_config)
        
        return OpenAIConfigResponse(
            id=str(existing_config.id),
            model_name=existing_config.model_name,
            input_price_per_1m=existing_config.input_price_per_1m,
            output_price_per_1m=existing_config.output_price_per_1m,
            is_active=existing_config.is_active,
            is_default=existing_config.is_default,
            description=existing_config.description,
            provider=existing_config.provider,
            api_key=None,
            base_url=existing_config.base_url,
            created_at=existing_config.created_at.isoformat() if existing_config.created_at else "",
            updated_at=existing_config.updated_at.isoformat() if existing_config.updated_at else ""
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def delete_config(
    model_name: str,
    db: Session = Depends(get_db)
):
    """Xóa config OpenAI khỏi database.
    
    Args:
        model_name: Tên model cần xóa config (string)
        db: Database session (dependency injection)
    
    Returns:
        dict: Dictionary chứa message thành công
    
    Raises:
        HTTPException:
            - HTTP 404 nếu config không tồn tại
            - HTTP 500 nếu có lỗi trong quá trình xóa
    
    Note:
        - Config được xóa vĩnh viễn, không thể undo
        - Config được commit vào database
    """
    try:
        deleted = OpenAIConfigService.delete_config(model_name, db)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Config for model {model_name} not found")
        
        db.commit()
        return {"message": f"Config for model {model_name} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

