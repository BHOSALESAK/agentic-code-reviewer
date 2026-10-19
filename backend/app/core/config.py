from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agentic AI Code Reviewer"
    app_env: str = "demo"
    log_level: str = "INFO"
    frontend_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    github_token: str | None = None
    github_webhook_secret: str | None = None
    llm_provider: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    database_url: str = "sqlite:///./agentic_code_reviewer.db"
    redis_url: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def demo_mode(self) -> bool:
        return self.app_env.lower() in {"demo", "development", "test"}

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origins.split(",") if origin.strip() and origin.strip() != "*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
