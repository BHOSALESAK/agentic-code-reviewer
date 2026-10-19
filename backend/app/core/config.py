from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agentic AI Code Reviewer"
    app_env: str = "demo"
    log_level: str = "INFO"
    frontend_origin: str = "http://localhost:5173"
    github_token: str | None = None
    github_webhook_secret: str | None = None
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    database_url: str | None = None
    redis_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def demo_mode(self) -> bool:
        return self.app_env.lower() in {"demo", "development", "test"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
