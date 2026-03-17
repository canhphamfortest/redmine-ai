"""Anthropic Claude provider implementation."""
import logging
from typing import Dict, Any, Tuple

import anthropic

from app.config import settings
from app.services.llm_provider.base import LLMProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    provider_name = "anthropic"

    def __init__(self, model: str, api_key: str = None, base_url: str = None):
        super().__init__(model=model, api_key=api_key or settings.anthropic_api_key, base_url=base_url)
        if not self.api_key:
            raise ValueError("Anthropic API key not configured.")
        self._client = anthropic.Anthropic(api_key=self.api_key, base_url=self.base_url)

    def get_client(self):
        return self._client

    def generate(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            content = ""
            if response and response.content:
                content = "".join(block.text for block in response.content if hasattr(block, "text"))
            usage_raw = getattr(response, "usage", None) or {}
            input_token = getattr(usage_raw, "input_tokens", None) or 0
            output_token = getattr(usage_raw, "output_tokens", None) or 0
            total_tokens = input_token + output_token
            prompt_token = max(0, total_tokens - output_token)
            
            usage_info = {
                "input_token": input_token,
                "output_token": output_token,
                "total_tokens": total_tokens,
                "prompt_token": prompt_token,
            }
            if content:
                return content, usage_info
            logger.error("Anthropic returned empty response")
            return "Xin lỗi, không nhận được phản hồi từ AI model.", usage_info
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return "Xin lỗi, đã xảy ra lỗi khi kết nối với AI model (Claude).", {}

