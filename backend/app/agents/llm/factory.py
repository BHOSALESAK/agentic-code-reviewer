from app.agents.llm.mock import MockProvider
from app.agents.llm.openai_compatible import OpenAICompatibleProvider
from app.agents.llm.provider import StructuredLLMProvider
from app.core.config import Settings


def build_provider(settings: Settings) -> StructuredLLMProvider:
    if settings.demo_mode or not settings.llm_provider:
        return MockProvider(max_retries=settings.llm_max_retries)
    if settings.llm_provider.lower() == "openai-compatible":
        if not settings.llm_base_url or not settings.llm_api_key or not settings.llm_model:
            raise ValueError("openai-compatible provider requires LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL")
        return OpenAICompatibleProvider(base_url=settings.llm_base_url, api_key=settings.llm_api_key, model=settings.llm_model, timeout_seconds=settings.llm_timeout_seconds, max_retries=settings.llm_max_retries)
    raise ValueError("unsupported LLM_PROVIDER; use openai-compatible or demo mode")
