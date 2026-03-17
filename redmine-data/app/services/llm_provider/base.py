"""Base abstractions for LLM providers."""
import abc
from typing import Dict, Tuple, Optional, Any


class LLMProvider(abc.ABC):
    """Base class for all LLM providers."""

    provider_name: str = "openai"

    def __init__(self, model: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    @abc.abstractmethod
    def generate(self, prompt: str) -> Tuple[str, Dict[str, Any]]:
        """Generate answer for a prompt.

        Returns:
            Tuple(answer, usage_info)
        """
        raise NotImplementedError

    def get_client(self):
        """Return underlying client if applicable."""
        return None

    def get_model(self) -> str:
        return self.model

