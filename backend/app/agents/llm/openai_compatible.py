from typing import Any

import httpx
from pydantic import BaseModel

from app.agents.llm.provider import LLMProviderError, StructuredLLMProvider


class OpenAICompatibleProvider(StructuredLLMProvider):
    def __init__(self, *, base_url: str, api_key: str, model: str, timeout_seconds: float = 20.0, **kwargs: Any):
        super().__init__(**kwargs)
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.client = httpx.Client(timeout=timeout_seconds)

    def _complete_once(self, prompt: str, response_model: type[BaseModel]) -> Any:
        try:
            response = self.client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}},
            )
        except httpx.RequestError as exc:
            raise LLMProviderError("LLM network request failed", transient=True) from exc
        if response.status_code in {408, 429} or response.status_code >= 500:
            raise LLMProviderError("LLM service temporarily unavailable", transient=True)
        if response.is_error:
            raise LLMProviderError("LLM provider rejected the request")
        payload = response.json()
        return payload["choices"][0]["message"]["content"]
