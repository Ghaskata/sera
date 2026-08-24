from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://sera:sera@localhost:5432/sera"

    telegram_bot_token: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/oauth/google/callback"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    gemini_embed_model: str = "text-embedding-004"

    token_encryption_key: str = ""

    drive_sync_interval_minutes: int = 15

    rag_min_similarity: float = 0.55
    rag_top_k: int = 5


settings = Settings()
