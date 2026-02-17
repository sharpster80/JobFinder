from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "")
    redis_url: str = os.getenv("REDIS_URL", "")
    resend_api_key: str = ""
    vapid_public_key: str = ""
    vapid_private_key: str = ""
    vapid_subject: str = ""
    notification_score_threshold: int = 90
    digest_hour: int = 8

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
