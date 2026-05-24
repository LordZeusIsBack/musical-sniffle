from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Therapy Chatbot Backend"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 120

    database_url: str = "postgresql+asyncpg://postgres:root@localhost:5432/therapy_chatbot"
    database_admin_url: str | None = None

    ollama_base_url: str = "http://localhost:11434/v1"
    generator_model: str = "llama3.1:8b-instruct-q4_K_M"
    safety_model: str = "shieldgemma:2b"

    decay_lambda: float = 0.1
    sensitivity_alpha: float = 0.3

    pseudonym_hmac_key: str = "pseudonym-key"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
