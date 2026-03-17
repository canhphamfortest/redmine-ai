"""Pydantic schemas cho LLM Config API (hỗ trợ OpenAI, Google, Anthropic, Groq).

Module này định nghĩa các request/response schemas cho LLM config endpoints:
- OpenAIConfigCreate: Schema cho tạo/cập nhật config
- OpenAIConfigUpdate: Schema cho cập nhật config (partial)
- OpenAIConfigResponse: Schema cho response config
"""
from pydantic import BaseModel
from typing import Optional


class OpenAIConfigCreate(BaseModel):
    """Schema cho request tạo hoặc cập nhật LLM config.
    
    Attributes:
        model_name: Tên model LLM (str). Ví dụ: "gpt-4o-mini", "gemini-1.5-pro", "claude-3-sonnet"
        input_price_per_1m: Giá cho mỗi 1M input tokens (float).
                           Ví dụ: 0.15 cho $0.15/1M tokens
        output_price_per_1m: Giá cho mỗi 1M output tokens (float).
                            Ví dụ: 0.6 cho $0.6/1M tokens
        is_active: Trạng thái active (bool, default: True).
                  Nếu False, model sẽ không được sử dụng
        description: Mô tả về config (str, optional)
    
    Note:
        - Nếu config đã tồn tại (theo model_name), sẽ được cập nhật
        - Nếu chưa tồn tại, sẽ được tạo mới
    """
    model_name: str
    input_price_per_1m: float
    output_price_per_1m: float
    is_active: bool = True
    description: Optional[str] = None
    provider: str = "openai"
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class OpenAIConfigUpdate(BaseModel):
    """Schema cho request cập nhật LLM config (partial update).
    
    Attributes:
        input_price_per_1m: Giá input tokens mới (float, optional)
        output_price_per_1m: Giá output tokens mới (float, optional)
        is_active: Trạng thái active mới (bool, optional)
        description: Mô tả mới (str, optional)
    
    Note:
        - Tất cả fields đều optional, chỉ cập nhật các fields được cung cấp
        - Không thể cập nhật model_name (phải tạo config mới)
    """
    input_price_per_1m: Optional[float] = None
    output_price_per_1m: Optional[float] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class OpenAIConfigResponse(BaseModel):
    """Schema cho response LLM config.
    
    Attributes:
        id: UUID của config (str)
        model_name: Tên model (str)
        input_price_per_1m: Giá input tokens (float)
        output_price_per_1m: Giá output tokens (float)
        is_active: Trạng thái active (bool)
        is_default: Có phải model mặc định không (bool)
        description: Mô tả config (str, optional)
        created_at: Thời gian tạo (str, ISO format)
        updated_at: Thời gian cập nhật (str, ISO format)
    """
    id: str
    model_name: str
    input_price_per_1m: float
    output_price_per_1m: float
    is_active: bool
    is_default: bool
    description: Optional[str]
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

