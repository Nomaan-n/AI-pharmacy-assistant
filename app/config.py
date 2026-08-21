from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AI Pharmacy Assistant"
    app_version: str = "2.0.0"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    daily_med_base_url: str = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
    request_timeout_seconds: float = 8.0
    max_question_length: int = 1000
    allow_origins: str = "*"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
