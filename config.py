from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    nvidia_api_key: str = Field(default="", alias="NVIDIA_API_KEY")
    ngc_api_key: str = Field(default="", alias="NGC_API_KEY")
    # Legacy fallback for older env files
    openrouter_api_key_legacy: str = Field(default="", alias="OPENROUTER_API_KEY")

    database_url: str = Field(alias="DATABASE_URL")

    openai_base_url: str = Field(default="https://integrate.api.nvidia.com/v1", alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="meta/llama-3.3-70b-instruct", alias="OPENAI_MODEL")
    ai_max_tokens: int = Field(default=1200, alias="AI_MAX_TOKENS")
    ai_user_daily_limit: int = Field(default=3, alias="AI_USER_DAILY_LIMIT")

    # Optional metadata
    app_url: str | None = Field(default=None, alias="APP_URL")
    app_name: str | None = Field(default="fitness-bot", alias="APP_NAME")

    default_water_norm_ml: int = Field(default=2000, alias="DEFAULT_WATER_NORM_ML")
    rate_limit_max_messages: int = Field(default=10, alias="RATE_LIMIT_MAX_MESSAGES")
    rate_limit_window_seconds: int = Field(default=10, alias="RATE_LIMIT_WINDOW_SECONDS")

    @property
    def llm_api_key(self) -> str:
        return (
            self.openai_api_key
            or self.nvidia_api_key
            or self.ngc_api_key
            or self.openrouter_api_key_legacy
        ).strip()


settings = Settings()
