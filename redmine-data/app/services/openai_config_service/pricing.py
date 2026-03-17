"""Các phương thức liên quan đến pricing cho LLM config (hỗ trợ nhiều providers)"""
from typing import Dict
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import LLMConfig
from app.services.openai_usage_tracker import OpenAIUsageTracker


def get_pricing_for_model(model_name: str, provider: str = "openai", use_db: bool = True) -> Dict[str, float]:
    """Lấy pricing cho một model theo provider, ưu tiên DB rồi fallback mặc định.
    
    Hàm này lấy pricing theo thứ tự ưu tiên:
    1. Database config (nếu use_db=True và tìm thấy active config)
    2. Hardcoded pricing từ OpenAIUsageTracker.PRICING
    
    Args:
        model_name: Tên model cần lấy pricing (string)
        use_db: Có kiểm tra database trước không (mặc định: True).
               Nếu False, chỉ sử dụng hardcoded pricing
    
    Returns:
        Dict[str, float]: Dictionary chứa:
            - input: Giá input tokens cho mỗi 1M tokens (float)
            - output: Giá output tokens cho mỗi 1M tokens (float)
    
    Note:
        - Database query chỉ lấy configs có is_active=True
        - Fallback về OpenAIUsageTracker.get_pricing() nếu không tìm thấy trong DB
        - Session được tự động đóng sau khi query
    """
    if use_db:
        db = SessionLocal()
        try:
            config = db.query(LLMConfig).filter(
                LLMConfig.model_name == model_name,
                LLMConfig.is_active == True
            ).first()
            
            if config:
                return {
                    "input": config.input_price_per_1m,
                    "output": config.output_price_per_1m
                }
        finally:
            db.close()
    
    provider_pricing = OpenAIUsageTracker.PRICING.get(provider or "openai", {})
    return provider_pricing.get(model_name, {})

