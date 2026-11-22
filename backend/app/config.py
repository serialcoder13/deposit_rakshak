"""
config.py — reads environment variables via pydantic-settings.
All LLM and runtime config lives here; never in code.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM — defaults to DeepSeek (OpenAI-compatible API)
    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"
    llm_vision_model: str = "deepseek-chat"
    llm_api_url: str = "https://api.deepseek.com"

    # Auth
    jwt_secret: str = "change-me-before-demo"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Demo
    demo_mode: bool = False
    demo_otp: str = "123456"

    # DB
    db_url: str = "sqlite:///./data/app.db"


settings = Settings()
