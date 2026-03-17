"""Thông tin pricing và tính toán chi phí cho các LLM providers"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Pricing cho mỗi 1M tokens (USD)
# Các giá trị mang tính tham khảo, cần cập nhật nếu nhà cung cấp thay đổi
PRICING = {
    "google": {
        # Gemini 3 series (Preview)
        "gemini-3-pro-preview": {"input": 2.00 / 1_000_000, "output": 12.00 / 1_000_000},  # <= 200k tokens pricing
        "gemini-3-flash-preview": {"input": 0.50 / 1_000_000, "output": 3.00 / 1_000_000},  # text/image/video pricing
        # Gemini 2.5 series
        "gemini-2.5-flash": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
        # Gemini 2.0 series
        "gemini-2.0-flash": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
        # Gemini 1.5 series
        "gemini-1.5-pro": {"input": 3.50 / 1_000_000, "output": 10.50 / 1_000_000},
        "gemini-1.5-flash": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
        # Gemini 1.0 series (legacy)
        "gemini-1.0-pro": {"input": 0.50 / 1_000_000, "output": 1.50 / 1_000_000},
        "gemini-pro": {"input": 0.50 / 1_000_000, "output": 1.50 / 1_000_000},  # Alias for gemini-1.0-pro
    },
    "anthropic": {
        "claude-3-opus": {"input": 15.00 / 1_000_000, "output": 75.00 / 1_000_000},
        "claude-3-sonnet": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
        "claude-3-haiku": {"input": 0.25 / 1_000_000, "output": 1.25 / 1_000_000},
    },
    "groq": {
        "llama-3.3-70b-versatile": {"input": 0.59 / 1_000_000, "output": 0.79 / 1_000_000},
        "llama2-70b-4096": {"input": 0.59 / 1_000_000, "output": 0.79 / 1_000_000},
        "mixtral-8x7b-32768": {"input": 0.27 / 1_000_000, "output": 0.27 / 1_000_000},
    },
    # GPT-4o series
    "openai": {
        "gpt-4o-mini": {
        "input": 0.150 / 1_000_000,  # $0.150 cho mỗi 1M input tokens
        "output": 0.600 / 1_000_000,  # $0.600 cho mỗi 1M output tokens
    },
        "gpt-4o": {
        "input": 2.50 / 1_000_000,   # $2.50 cho mỗi 1M input tokens
        "output": 10.00 / 1_000_000, # $10.00 cho mỗi 1M output tokens
    },
        "gpt-4o-2024-08-06": {
        "input": 2.50 / 1_000_000,
        "output": 10.00 / 1_000_000,
    },
    # GPT-4 Turbo
        "gpt-4-turbo": {
        "input": 10.00 / 1_000_000,  # $10.00 cho mỗi 1M input tokens
        "output": 30.00 / 1_000_000, # $30.00 cho mỗi 1M output tokens
    },
        "gpt-4-turbo-preview": {
        "input": 10.00 / 1_000_000,
        "output": 30.00 / 1_000_000,
    },
    # GPT-4
        "gpt-4": {
        "input": 30.00 / 1_000_000,  # $30.00 cho mỗi 1M input tokens
        "output": 60.00 / 1_000_000, # $60.00 cho mỗi 1M output tokens
    },
        "gpt-4-32k": {
        "input": 60.00 / 1_000_000,  # $60.00 cho mỗi 1M input tokens
        "output": 120.00 / 1_000_000, # $120.00 cho mỗi 1M output tokens
    },
    # GPT-3.5 Turbo (legacy)
        "gpt-3.5-turbo": {
        "input": 0.50 / 1_000_000,   # $0.50 cho mỗi 1M input tokens
        "output": 1.50 / 1_000_000,   # $1.50 cho mỗi 1M output tokens
    },
    # GPT-5 series (newer models)
        "gpt-5-nano": {
        "input": 0.05 / 1_000_000,    # $0.05 cho mỗi 1M input tokens (từ tài liệu OpenAI)
        "output": 0.40 / 1_000_000,   # $0.40 cho mỗi 1M output tokens (từ tài liệu OpenAI)
    },
        "gpt-5": {
        "input": 2.00 / 1_000_000,    # Ước tính, cập nhật khi có pricing chính thức
        "output": 8.00 / 1_000_000,   # Ước tính, cập nhật khi có pricing chính thức
    },
    # o1 series (reasoning models - không hỗ trợ temperature)
        "o1-preview": {
        "input": 15.00 / 1_000_000,   # $15.00 cho mỗi 1M input tokens
        "output": 60.00 / 1_000_000,  # $60.00 cho mỗi 1M output tokens
    },
        "o1-mini": {
        "input": 3.00 / 1_000_000,    # $3.00 cho mỗi 1M input tokens
        "output": 12.00 / 1_000_000,  # $12.00 cho mỗi 1M output tokens
    },
    },
}


def get_fallback_pricing(model: str) -> Dict[str, float]:
    """Lấy pricing fallback dựa trên model family.
    
    Hàm này khớp các pattern trong tên model để tìm pricing tier phù hợp
    khi model cụ thể không có trong PRICING dictionary. Hỗ trợ các model families:
    o1, GPT-5, GPT-4o, GPT-4 Turbo, GPT-4, GPT-3.5.
    
    Args:
        model: Tên model cần tìm pricing (string).
               Ví dụ: "gpt-5-nano", "gpt-4o-2024-08-06", "o1-mini"
    
    Returns:
        Dict[str, float]: Dictionary pricing với:
            - input: Giá input tokens cho mỗi 1M tokens (float)
            - output: Giá output tokens cho mỗi 1M tokens (float)
    
    Note:
        - Khớp pattern theo thứ tự ưu tiên: o1 > GPT-5 > GPT-4o > GPT-4 Turbo > GPT-4 > GPT-3.5
        - Fallback về gpt-4o-mini pricing nếu không khớp pattern nào
        - Log warning khi sử dụng fallback pricing
    """
    model_lower = model.lower()
    
    openai_pricing = PRICING.get("openai", {})

    # o1 series (reasoning models)
    if "o1" in model_lower:
        if "mini" in model_lower:
            return openai_pricing.get("o1-mini", openai_pricing.get("gpt-4o", {"input": 0, "output": 0}))
        else:
            return openai_pricing.get("o1-preview", openai_pricing.get("gpt-4o", {"input": 0, "output": 0}))
    
    # GPT-5 series
    if "gpt-5" in model_lower:
        if "nano" in model_lower:
            return openai_pricing.get("gpt-5-nano", openai_pricing.get("gpt-4o-mini", {"input": 0, "output": 0}))
        else:
            return openai_pricing.get("gpt-5", openai_pricing.get("gpt-4o", {"input": 0, "output": 0}))
    
    # GPT-4o series
    if "gpt-4o" in model_lower:
        if "mini" in model_lower:
            return openai_pricing.get("gpt-4o-mini", {"input": 0, "output": 0})
        else:
            return openai_pricing.get("gpt-4o-2024-08-06", openai_pricing.get("gpt-4o", {"input": 0, "output": 0}))
    
    # GPT-4 Turbo
    if "gpt-4" in model_lower and "turbo" in model_lower:
        if "preview" in model_lower:
            return openai_pricing.get("gpt-4-turbo-preview", openai_pricing.get("gpt-4-turbo", {"input": 0, "output": 0}))
        else:
            return openai_pricing.get("gpt-4-turbo", openai_pricing.get("gpt-4o", {"input": 0, "output": 0}))
    
    # GPT-4 standard
    if "gpt-4" in model_lower:
        if "32k" in model_lower:
            return openai_pricing.get("gpt-4-32k", openai_pricing.get("gpt-4", {"input": 0, "output": 0}))
        else:
            return openai_pricing.get("gpt-4", openai_pricing.get("gpt-4o", {"input": 0, "output": 0}))
    
    # GPT-3.5 Turbo (legacy)
    if "gpt-3.5" in model_lower or "gpt-35" in model_lower:
        if "turbo" in model_lower:
            return openai_pricing.get("gpt-3.5-turbo", openai_pricing.get("gpt-4o-mini", {"input": 0, "output": 0}))
    
    # Mặc định về tùy chọn rẻ nhất (gpt-4o-mini) cho các model không xác định
    logger.warning(f"Unknown model family for {model}, defaulting to gpt-4o-mini pricing")
    return openai_pricing.get("gpt-4o-mini", {"input": 0, "output": 0})


def calculate_cost(model: str, input_token: int, output_token: int) -> float:
    """Tính chi phí dựa trên token usage.
    
    Hàm này tính toán chi phí cho việc sử dụng OpenAI API dựa trên số lượng
    input và output tokens. Pricing được lấy theo thứ tự ưu tiên:
    1. Database config (nếu có)
    2. PRICING dictionary (hardcoded)
    3. Fallback pricing dựa trên model family
    
    Args:
        model: Tên model OpenAI (string). Ví dụ: "gpt-4o-mini", "gpt-5-nano"
        input_token: Số lượng input tokens đã sử dụng (int)
        output_token: Số lượng output tokens đã sử dụng (int)
    
    Returns:
        float: Chi phí tính bằng USD (tổng của input_cost + output_cost)
    
    Note:
        - Pricing được lấy từ database trước (nếu use_db=True)
        - Fallback về PRICING dictionary nếu không có trong DB
        - Nếu model không có trong PRICING, sử dụng get_fallback_pricing()
        - Log warning khi sử dụng fallback pricing
        - Chi phí = (input_token * input_price) + (output_token * output_price)
    """
def calculate_cost(model: str, input_token: int, output_token: int, provider: str = "openai") -> float:
    """Tính chi phí dựa trên token usage cho nhiều providers."""
    pricing = None
    try:
        from app.services.openai_config_service import OpenAIConfigService
        pricing = OpenAIConfigService.get_pricing_for_model(model, provider=provider, use_db=True)
    except Exception as e:
        logger.debug(f"Failed to get pricing from database for {provider}:{model}: {e}")
    
    provider_pricing = PRICING.get(provider or "openai", {})
    if not pricing:
        pricing = provider_pricing.get(model)
        if not pricing:
            if provider == "openai":
                pricing = get_fallback_pricing(model)
                logger.warning(
                    f"Unknown model pricing for {provider}:{model}, using fallback pricing: "
                    f"input=${pricing['input']*1_000_000:.3f}/1M, output=${pricing['output']*1_000_000:.3f}/1M"
                )
            else:
                logger.warning(f"Unknown model pricing for {provider}:{model}, defaulting to 0.")
                pricing = {"input": 0, "output": 0}
    
    input_cost = input_token * pricing["input"]
    output_cost = output_token * pricing["output"]
    
    return input_cost + output_cost

