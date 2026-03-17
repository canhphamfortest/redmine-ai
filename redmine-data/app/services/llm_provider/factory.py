"""Factory helper to build LLM providers."""
from typing import Optional

from app.services.llm_provider.base import LLMProvider
from app.services.llm_provider.openai_provider import OpenAIProvider
from app.services.llm_provider.google_provider import GoogleProvider
from app.services.llm_provider.anthropic_provider import AnthropicProvider
from app.services.llm_provider.groq_provider import GroqProvider


PROVIDER_MAP = {
    "openai": OpenAIProvider,
    "google": GoogleProvider,
    "anthropic": AnthropicProvider,
    "groq": GroqProvider,
}


def get_provider(
    provider_name: str,
    model: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    service_account_path: Optional[str] = None,
) -> LLMProvider:
    provider_cls = PROVIDER_MAP.get(provider_name or "openai")
    if not provider_cls:
        raise ValueError(f"Unsupported provider: {provider_name}")
    
    # GoogleProvider supports service account, others don't
    if provider_name == "google" and service_account_path:
        return provider_cls(
            model=model, 
            api_key=api_key, 
            base_url=base_url,
            service_account_path=service_account_path
        )
    else:
        return provider_cls(model=model, api_key=api_key, base_url=base_url)

