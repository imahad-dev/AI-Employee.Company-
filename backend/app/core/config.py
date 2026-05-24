from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    app_name: str = "Autonomous AI Software Company"
    database_path: Path = Field(default=Path("data/platform.db"), alias="DATABASE_PATH")
    workspace_root: Path = Field(default=Path("../workspace"), alias="WORKSPACE_ROOT")
    provider_mode: str = Field(default="mock", alias="PROVIDER_MODE")
    provider_timeout_seconds: float = Field(default=120.0, alias="PROVIDER_TIMEOUT_SECONDS")

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514", alias="ANTHROPIC_MODEL")
    anthropic_max_tokens: int = Field(default=4096, alias="ANTHROPIC_MAX_TOKENS")
    anthropic_temperature: float = Field(default=0.2, alias="ANTHROPIC_TEMPERATURE")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")

    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_base_url: str = Field(default="https://generativelanguage.googleapis.com/v1beta", alias="GEMINI_BASE_URL")
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")
    groq_model: str = Field(default="llama-3.3-70b-versatile", alias="GROQ_MODEL")

    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")
    openrouter_model: str = Field(default="anthropic/claude-3.5-sonnet", alias="OPENROUTER_MODEL")
    openrouter_site_url: str | None = Field(default=None, alias="OPENROUTER_SITE_URL")
    openrouter_app_name: str = Field(default="AI Software Company", alias="OPENROUTER_APP_NAME")

    local_base_url: str = Field(default="http://localhost:11434/v1", alias="LOCAL_BASE_URL")
    local_api_key: str = Field(default="local", alias="LOCAL_API_KEY")
    local_model: str = Field(default="llama3.1", alias="LOCAL_MODEL")

    max_pipeline_loops: int = Field(default=10, alias="MAX_PIPELINE_LOOPS")
    summarizer_interval: int = Field(default=3, alias="SUMMARIZER_INTERVAL")
    budget_warning_usd: float = Field(default=10.0, alias="BUDGET_WARNING_USD")


@lru_cache
def get_settings() -> Settings:
    return Settings()
