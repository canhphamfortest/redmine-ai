"""OpenAI provider implementation."""
import logging
from typing import Dict, Any, Tuple
from openai import OpenAI

from app.config import settings
from app.services.llm_provider.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    provider_name = "openai"

    def __init__(self, model: str, api_key: str = None, base_url: str = None):
        super().__init__(model=model, api_key=api_key or settings.openai_api_key, base_url=base_url)
        if not self.api_key:
            raise ValueError("OpenAI API key not configured.")
        self._client = OpenAI(api_key=self.api_key, base_url=self.base_url, max_retries=0)

    def get_client(self):
        return self._client

    def generate(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                timeout=360,
            )
            input_token = response.usage.prompt_tokens if response.usage else 0
            output_token = response.usage.completion_tokens if response.usage else 0
            total_tokens = response.usage.total_tokens if response.usage else 0
            prompt_token = max(0, total_tokens - output_token)
            
            usage_info = {
                "input_token": input_token,
                "output_token": output_token,
                "total_tokens": total_tokens,
                "prompt_token": prompt_token,
            }
            if response.choices and len(response.choices) > 0:
                answer = response.choices[0].message.content or ""
                return answer, usage_info
            logger.error("OpenAI API returned empty response")
            return "Xin lỗi, không nhận được phản hồi từ AI model.", usage_info
        except Exception as e:
            error_msg = str(e).lower()
            if "api key" in error_msg or "authentication" in error_msg:
                logger.error("OpenAI generation failed: Authentication error")
                return "Xin lỗi, lỗi xác thực OpenAI API. Vui lòng kiểm tra OPENAI_API_KEY.", {}
            if "rate limit" in error_msg:
                logger.error("OpenAI generation failed: Rate limit exceeded")
                return "Xin lỗi, đã vượt quá giới hạn API. Vui lòng thử lại sau.", {}
            logger.error(f"OpenAI generation failed: {str(e)}")
            return "Xin lỗi, đã xảy ra lỗi khi kết nối với AI model.", {}

