"""Logic tạo OpenAI cho RAG chain.

Module này cung cấp các functions để generate answer từ OpenAI API:
- generate_answer: Gọi OpenAI API để tạo answer từ prompt
- is_error_response: Kiểm tra xem response có phải là error không
- Error detection helpers: Các helper functions để phát hiện lỗi

Xử lý các lỗi phổ biến (authentication, rate limit, connection) và trả về
error messages phù hợp bằng tiếng Việt.
"""
import logging
from typing import Tuple, Dict, Any
from openai import OpenAI

from app.config import settings
from app.services.openai_usage_tracker import OpenAIUsageTracker

logger = logging.getLogger(__name__)


def is_error_response(answer: str, usage_info: dict) -> bool:
    """
    Kiểm tra xem response có phải là error response không
    
    Args:
        answer: Văn bản answer đã tạo
        usage_info: Thông tin usage từ API
        
    Returns:
        True nếu response báo lỗi
    """
    if _check_empty_response(answer, usage_info):
        return True
    
    if _check_error_keywords(answer, usage_info):
        return True
    
    if _check_error_patterns(answer):
        return True
    
    return False


def _check_empty_response(answer: str, usage_info: dict) -> bool:
    """Kiểm tra xem response có rỗng hoặc usage_info có báo lỗi không.
    
    Hàm này kiểm tra các dấu hiệu cho thấy response là lỗi:
    - Answer rỗng hoặc None
    - usage_info rỗng ({}), điều này xảy ra khi có exception trong quá trình generate
    
    Args:
        answer: Văn bản answer từ LLM (string)
        usage_info: Dictionary chứa thông tin usage tokens (dict)
    
    Returns:
        bool: True nếu response rỗng hoặc usage_info rỗng, False nếu không
    
    Note:
        - usage_info rỗng ({}) là dấu hiệu chắc chắn của lỗi
        - Điều này xảy ra khi generate_answer() catch exception và trả về {}
    """
    if not answer:
        return True
    
    # Nếu usage_info rỗng ({}), chắc chắn là lỗi
    # Điều này xảy ra khi _generate bắt được exception
    if not usage_info:
        return True
    
    return False


def _check_error_keywords(answer: str, usage_info: dict) -> bool:
    """Kiểm tra xem answer có chứa error keywords không khi total_tokens là 0.
    
    Hàm này kiểm tra các trường hợp đặc biệt: khi total_tokens = 0 (không có
    API call thực sự) nhưng answer có chứa các từ khóa lỗi. Điều này có thể
    xảy ra khi có lỗi trong quá trình xử lý nhưng vẫn trả về error message.
    
    Args:
        answer: Văn bản answer từ LLM (string)
        usage_info: Dictionary chứa thông tin usage tokens, đặc biệt total_tokens (dict)
    
    Returns:
        bool: True nếu total_tokens = 0 và answer chứa error keywords, False nếu không
    
    Note:
        - Chỉ kiểm tra khi total_tokens = 0
        - Error keywords được viết bằng tiếng Việt
        - So sánh không phân biệt hoa thường
    """
    total_tokens = usage_info.get('total_tokens', 0)
    if total_tokens == 0:
        error_keywords = [
            'xin lỗi, lỗi',
            'xin lỗi, đã xảy ra lỗi',
            'xin lỗi, không nhận được phản hồi',
            'xin lỗi, đã vượt quá giới hạn',
            'xin lỗi, lỗi xác thực'
        ]
        answer_lower = answer.lower()
        for keyword in error_keywords:
            if keyword in answer_lower:
                return True
    
    return False


def _check_error_patterns(answer: str) -> bool:
    """Kiểm tra các error patterns cụ thể cho thấy lỗi API/system.
    
    Hàm này kiểm tra các thông báo lỗi được hardcode từ exception handlers
    trong generate_answer(). Các patterns này là các thông báo lỗi chuẩn
    được trả về khi có lỗi xác thực, rate limit, hoặc connection.
    
    Args:
        answer: Văn bản answer từ LLM (string)
    
    Returns:
        bool: True nếu answer chứa bất kỳ error pattern nào, False nếu không
    
    Note:
        - Error patterns được viết bằng tiếng Việt
        - So sánh không phân biệt hoa thường
        - Các patterns này được hardcode từ exception handlers
    """
    # Đây là các thông báo lỗi được hardcode từ exception handler của _generate
    error_patterns = [
        'xin lỗi, lỗi xác thực openai api',
        'xin lỗi, đã vượt quá giới hạn api',
        'xin lỗi, không nhận được phản hồi từ ai model',
        'xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi'
    ]
    
    answer_lower = answer.lower()
    for pattern in error_patterns:
        if pattern in answer_lower:
            return True
    
    return False


def generate_answer(
    client: OpenAI,
    model: str,
    prompt: str
) -> Tuple[str, Dict[str, Any]]:
    """Tạo answer từ LLM sử dụng OpenAI chat.completions API.
    
    Hàm này gọi OpenAI API để tạo answer từ prompt. Xử lý các lỗi phổ biến
    (authentication, rate limit, connection) và trả về error message phù hợp.
    
    Quy trình:
    1. Gọi OpenAI chat.completions.create() với prompt
    2. Trích xuất answer từ response.choices[0].message.content
    3. Trích xuất usage info (tokens) từ response.usage
    4. Xử lý các exception và trả về error message phù hợp
    
    Args:
        client: OpenAI client instance đã được khởi tạo với API key
        model: Tên model OpenAI để sử dụng (vd: "gpt-4o-mini")
        prompt: Prompt hoàn chỉnh để gửi đến LLM (string)
    
    Returns:
        Tuple[str, Dict[str, Any]]: Tuple chứa:
            - answer: Văn bản answer từ LLM, hoặc error message nếu có lỗi
            - usage_info: Dictionary chứa:
                - input_token: Số token input (prompt_tokens)
                - output_token: Số token output (completion_tokens)
                - total_tokens: Tổng số tokens
                - Rỗng ({}) nếu có lỗi
    
    Raises:
        Exception: Các exception từ OpenAI API được catch và convert thành error message
    
    Note:
        - Timeout được set là 360 giây (6 phút)
        - Nếu response rỗng, trả về error message
        - Các lỗi được phân loại: authentication, rate limit, hoặc generic
        - Error messages được viết bằng tiếng Việt
    """
    try:
        # Sử dụng chat.completions API (OpenAI API chuẩn)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            timeout=360
        )
        
        # Trích xuất thông tin usage
        # OpenAI API sử dụng prompt_tokens và completion_tokens, không phải input_token/output_token
        usage_info = {
            'input_token': response.usage.prompt_tokens if response.usage else 0,
            'output_token': response.usage.completion_tokens if response.usage else 0,
            'total_tokens': response.usage.total_tokens if response.usage else 0
        }
        
        if response.choices and len(response.choices) > 0:
            answer = response.choices[0].message.content or ""
            return answer, usage_info
        else:
            logger.error(f"OpenAI API returned empty response")
            return "Xin lỗi, không nhận được phản hồi từ AI model.", usage_info
            
    except Exception as e:
        # Ghi log lỗi không có full traceback
        error_msg = str(e).lower()
        if "api key" in error_msg or "authentication" in error_msg:
            logger.error("OpenAI generation failed: Authentication error")
            return f"Xin lỗi, lỗi xác thực OpenAI API. Vui lòng kiểm tra OPENAI_API_KEY.", {}
        elif "rate limit" in error_msg:
            logger.error("OpenAI generation failed: Rate limit exceeded")
            return f"Xin lỗi, đã vượt quá giới hạn API. Vui lòng thử lại sau.", {}
        else:
            logger.error(f"OpenAI generation failed: {str(e)}")
            return f"Xin lỗi, đã xảy ra lỗi khi kết nối với AI model.", {}

