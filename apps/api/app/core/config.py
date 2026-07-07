from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "local"
    # SQLite works without Docker; use PostgreSQL in production (see .env.example)
    database_url: str = "sqlite:///./krai_local.db"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin123"
    s3_bucket: str = "krai-recordings"
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = False
    storage_backend: str = "auto"  # auto | s3 | local
    local_storage_dir: str = "local_recordings"

    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"
    allowed_origins: str = "http://localhost:3000"

    whisper_model: str = "base"
    whisper_device: str = "cpu"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"

    google_client_id: str = ""
    google_client_secret: str = ""

    redis_url: str = "redis://localhost:6379/0"
    use_celery: bool = False

    rate_limit: str = "60/minute"

    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
