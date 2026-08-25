from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://sera:sera@localhost:5432/sera"

    telegram_bot_token: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/oauth/google/callback"
    google_maps_api_key: str = ""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    gemini_embed_model: str = "text-embedding-004"

    token_encryption_key: str = ""

    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_oauth_redirect_uri: str = "http://localhost:8000/oauth/slack/callback"

    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = "common"
    microsoft_oauth_redirect_uri: str = "http://localhost:8000/oauth/microsoft/callback"

    drive_sync_interval_minutes: int = 15
    meeting_sync_max_records: int = 100
    notes_sync_max_records: int = 100

    chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 50
    vector_store_backend: str = "pgvector"
    chroma_persist_dir: str = "./.chroma"
    chroma_collection_name: str = "sera_chunks"
    pinecone_api_key: str = ""
    pinecone_index_host: str = ""
    pinecone_namespace: str = "sera"

    start_telegram_in_web: bool = True
    start_scheduler_in_web: bool = True

    rag_query_token: str = ""
    rag_min_similarity: float = 0.55
    rag_top_k: int = 5


settings = Settings()
