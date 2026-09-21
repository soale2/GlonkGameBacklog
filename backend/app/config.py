from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"  # "development" | "production"
    database_url: str = "sqlite:///./glonk.db"
    session_secret: str = "dev-secret-change-me"

    igdb_client_id: str = ""
    igdb_client_secret: str = ""

    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_redirect_uri: str = "http://localhost:8000/api/auth/callback"
    discord_bot_token: str = ""

    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
