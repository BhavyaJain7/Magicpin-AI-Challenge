"""Application configuration using Pydantic Settings."""

import os
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Bot Metadata
    TEAM_NAME: str = "magicpin-ai-team"
    TEAM_MEMBERS: List[str] = Field(default_factory=lambda: ["Lead Engineer"])
    BOT_VERSION: str = "1.0.0"
    MODEL_NAME: str = "gemini-1.5-flash"
    APPROACH: str = "Deterministic policy & state machine + 4-context grounded LLM composer with verification"
    CONTACT_EMAIL: str = "team@magicpin.in"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8080
    DEBUG: bool = False

    # Storage settings
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_IN_MEMORY_STATE: bool = True  # Resilient fallback if Redis is absent

    # LLM Settings
    LLM_PROVIDER: str = "gemini"  # "openai", "gemini", "anthropic", "mock"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""


settings = Settings()
