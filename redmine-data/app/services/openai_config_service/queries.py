"""Các phương thức query database cho LLM config (hỗ trợ nhiều providers)"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import LLMConfig


def get_all_configs(db: Session = None, provider: str = None) -> List[LLMConfig]:
    """Lấy tất cả config OpenAI từ database.
    
    Args:
        db: Database session (tùy chọn). Nếu None, tạo session mới và đóng sau khi xong
    
    Returns:
        List[OpenAIConfig]: Danh sách tất cả configs, được sắp xếp theo model_name
    
    Note:
        - Session được tự động đóng nếu được tạo trong hàm
        - Configs được sắp xếp theo tên model (alphabetical)
    """
    if db is None:
        db = SessionLocal()
        try:
            return get_all_configs(db, provider=provider)
        finally:
            db.close()
    
    query = db.query(LLMConfig)
    if provider:
        query = query.filter(LLMConfig.provider == provider)
    return query.order_by(LLMConfig.model_name).all()


def get_active_configs(db: Session = None, provider: str = None) -> List[LLMConfig]:
    """Lấy tất cả config OpenAI đang active từ database.
    
    Args:
        db: Database session (tùy chọn). Nếu None, tạo session mới và đóng sau khi xong
    
    Returns:
        List[OpenAIConfig]: Danh sách configs có is_active=True, được sắp xếp theo model_name
    
    Note:
        - Session được tự động đóng nếu được tạo trong hàm
        - Chỉ trả về configs có is_active=True
        - Configs được sắp xếp theo tên model (alphabetical)
    """
    if db is None:
        db = SessionLocal()
        try:
            return get_active_configs(db, provider=provider)
        finally:
            db.close()
    
    query = db.query(LLMConfig).filter(LLMConfig.is_active == True)
    if provider:
        query = query.filter(LLMConfig.provider == provider)
    return query.order_by(LLMConfig.model_name).all()


def get_config_by_model(model_name: str, db: Session = None, provider: str = None) -> Optional[LLMConfig]:
    """Lấy config cho một model cụ thể từ database.
    
    Args:
        model_name: Tên model cần lấy config (string)
        db: Database session (tùy chọn). Nếu None, tạo session mới và đóng sau khi xong
    
    Returns:
        OpenAIConfig | None: Config object nếu tìm thấy, None nếu không
    
    Note:
        - Session được tự động đóng nếu được tạo trong hàm
        - Query tìm chính xác theo model_name
    """
    if db is None:
        db = SessionLocal()
        try:
            return get_config_by_model(model_name, db, provider=provider)
        finally:
            db.close()
    
    query = db.query(LLMConfig).filter(LLMConfig.model_name == model_name)
    if provider:
        query = query.filter(LLMConfig.provider == provider)
    return query.first()

