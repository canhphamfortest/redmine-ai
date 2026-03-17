"""Groq provider implementation (OpenAI-compatible)."""
import logging
from typing import Dict, Any, Tuple

from groq import Groq

from app.config import settings
from app.services.llm_provider.base import LLMProvider

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    provider_name = "groq"

    def __init__(self, model: str, api_key: str = None, base_url: str = None):
        super().__init__(model=model, api_key=api_key or settings.groq_api_key, base_url=base_url)
        if not self.api_key:
            raise ValueError("Groq API key not configured.")
        self._client = Groq(api_key=self.api_key, base_url=self.base_url)

    def get_client(self):
        return self._client

    def generate(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                timeout=360,
            )
            usage = getattr(response, "usage", None) or {}
            input_token = getattr(usage, "prompt_tokens", None) or 0
            output_token = getattr(usage, "completion_tokens", None) or 0
            total_tokens = getattr(usage, "total_tokens", None) or 0
            prompt_token = max(0, total_tokens - output_token)
            
            usage_info = {
                "input_token": input_token,
                "output_token": output_token,
                "total_tokens": total_tokens,
                "prompt_token": prompt_token,
            }
            if response.choices:
                return response.choices[0].message.content or "", usage_info
            logger.error("Groq API returned empty response")
            return "Xin lỗi, không nhận được phản hồi từ AI model.", usage_info
        except Exception as e:
            logger.error(f"Groq generation failed: {e}")
            return "Xin lỗi, đã xảy ra lỗi khi kết nối với AI model (Groq).", {}

