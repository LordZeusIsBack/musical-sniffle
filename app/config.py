from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Therapy Chatbot Backend"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 120

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/therapy_chatbot"
    database_admin_url: str | None = None

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    decay_lambda: float = 0.1
    sensitivity_alpha: float = 0.3

    pseudonym_hmac_key: str = "pseudonym-key"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
