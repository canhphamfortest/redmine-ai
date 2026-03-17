"""LLM usage tracker - lớp chính để ghi log usage (hỗ trợ OpenAI, Google, Anthropic, Groq)"""
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import LLMUsageLog, LLMUsageLogDetail
from app.database import SessionLocal
from app.services.openai_usage_tracker.pricing import calculate_cost

logger = logging.getLogger(__name__)


class OpenAIUsageTracker:
    """Theo dõi usage LLM API (tokens và chi phí) - hỗ trợ nhiều providers.
    
    Class này cung cấp các phương thức để log và track việc sử dụng LLM API,
    bao gồm tokens, chi phí, và response times. Hỗ trợ OpenAI, Google, Anthropic, Groq.
    Tất cả methods là static methods.
    """
    
    @staticmethod
    def log_usage(
        model: str,
        input_token: int,
        output_token: int,
        total_tokens: Optional[int] = None,
        prompt_token: Optional[int] = None,
        user_query: Optional[str] = None,
        cached: bool = False,
        response_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None,
        provider: str = "openai",
    ) -> LLMUsageLog:
        """Ghi log LLM API usage vào database.
        
        Hàm này tạo một bản ghi LLMUsageLog với thông tin về provider, model, tokens,
        chi phí, và các metadata khác. Chi phí được tính tự động dựa trên pricing.
        
        Args:
            model: Tên model LLM đã sử dụng (string)
            input_token: Số lượng input tokens (int)
            output_token: Số lượng output tokens (int)
            total_tokens: Tổng tokens (tùy chọn). Nếu None, được tính = input_token + output_token
            user_query: Query gốc của người dùng (string, tùy chọn)
            cached: Response có được cache không (mặc định: False)
            response_time_ms: Thời gian phản hồi tính bằng milliseconds (int, tùy chọn)
            metadata: Metadata bổ sung dưới dạng dictionary (tùy chọn)
            db: Database session (tùy chọn). Nếu None, tạo session mới và commit
        
        Returns:
            LLMUsageLog: Instance đã được tạo và lưu vào database
        
        Raises:
            Exception: Nếu có lỗi trong quá trình lưu vào database
        
        Note:
            - Chi phí được tính tự động bằng calculate_cost()
            - Session được tự động commit và đóng nếu được tạo trong hàm
            - Metadata được lưu dưới dạng JSON trong extra_metadata field
        """
        # Tính tổng tokens nếu không được cung cấp
        if total_tokens is None:
            total_tokens = input_token + output_token
        
        # Tính chi phí
        cost = calculate_cost(model, input_token, output_token, provider=provider or "openai")
        
        # Tạo log entry
        usage_log = LLMUsageLog(
            provider=provider or "openai",
            model=model,
            input_token=input_token,
            output_token=output_token,
            total_tokens=total_tokens,
            prompt_token=prompt_token,
            cost_usd=cost,
            user_query=user_query,
            cached=cached,
            response_time_ms=response_time_ms,
            extra_metadata=metadata or {}
        )
        
        # Lưu vào database
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            db.add(usage_log)
            db.commit()
            db.refresh(usage_log)
            logger.debug(f"Logged LLM usage: {provider} {model} - {total_tokens} tokens, ${cost:.6f}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to log LLM usage: {e}", exc_info=True)
            raise
        finally:
            if should_close:
                db.close()
        
        return usage_log
    
    @staticmethod
    def log_usage_detail(
        usage_log_id: Any,
        prompt: str,
        response: Optional[str] = None,
        db: Optional[Session] = None
    ) -> LLMUsageLogDetail:
        """Ghi log chi tiết prompt và response cho OpenAI API usage.
        
        Hàm này tạo một bản ghi OpenAIUsageLogDetail chứa prompt đầy đủ và response
        để có thể review và debug sau này. Được gọi sau khi log_usage() thành công.
        
        Args:
            usage_log_id: ID của OpenAIUsageLog entry đã tạo trước đó (UUID hoặc string)
            prompt: Prompt đầy đủ đã gửi đến OpenAI (string)
            response: Response đầy đủ từ OpenAI (string, tùy chọn)
            db: Database session (tùy chọn). Nếu None, tạo session mới và commit
        
        Returns:
            OpenAIUsageLogDetail: Instance đã được tạo và lưu vào database
        
        Raises:
            Exception: Nếu có lỗi trong quá trình lưu vào database
        
        Note:
            - Liên kết với OpenAIUsageLog thông qua usage_log_id
            - Prompt và response có thể rất dài, được lưu trong database
            - Session được tự động commit và đóng nếu được tạo trong hàm
            - Response có thể None nếu chỉ muốn log prompt
        """
        # Tạo detail entry
        usage_detail = LLMUsageLogDetail(
            usage_log_id=usage_log_id,
            prompt=prompt,
            response=response
        )
        
        # Lưu vào database
        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        
        try:
            db.add(usage_detail)
            db.commit()
            db.refresh(usage_detail)
            logger.debug(f"Logged OpenAI usage detail for usage_log_id: {usage_log_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to log OpenAI usage detail: {e}", exc_info=True)
            raise
        finally:
            if should_close:
                db.close()
        
        return usage_detail

