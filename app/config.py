from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "AI Pharmacy Assistant"
    app_version: str = "2.4.0"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    daily_med_base_url: str = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
    india_drug_db_url: str = "https://drugdb.in"
    rxnorm_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    pubchem_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    request_timeout_seconds: float = 8.0
    max_question_length: int = 1000
    allow_origins: str = "*"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
