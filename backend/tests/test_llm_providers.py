import pytest
from pydantic import BaseModel

from app.agents.llm.mock import MockProvider
from app.agents.llm.provider import LLMProviderError


class Answer(BaseModel):
    value: int


class RetryingMockProvider(MockProvider):
    def _complete_once(self, prompt: str, response_model: type[BaseModel]):
        if self.calls == 0:
            self.calls += 1
            raise LLMProviderError("temporary", transient=True)
        return {"value": 7}


def test_provider_retries_transient_failure_and_records_usage() -> None:
    provider = RetryingMockProvider(max_retries=1)
    result = provider.complete_structured("return seven", Answer)
    assert result.value.value == 7
    assert result.usage.requests == 2
    assert result.usage.output_tokens > 0


def test_mock_provider_rejects_invalid_json_without_retry() -> None:
    provider = MockProvider(failure_modes=["invalid_json"], max_retries=2)
    with pytest.raises(LLMProviderError, match="validation failed"):
        provider.complete_structured("prompt", Answer)
    assert provider.usage.requests == 1


def test_mock_provider_retries_timeout_and_rate_limit() -> None:
    provider = MockProvider(failure_modes=["timeout", "rate_limit", "invalid_json"], max_retries=2)
    with pytest.raises(LLMProviderError):
        provider.complete_structured("prompt", Answer)
    assert provider.usage.requests == 3
