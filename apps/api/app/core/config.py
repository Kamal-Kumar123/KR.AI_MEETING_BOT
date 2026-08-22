from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _API_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

    # Cloud AI (Deepgram STT + Gemini LLM)
    deepgram_api_key: str = ""
    deepgram_model: str = "nova-2"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_extension_client_id: str = ""

    redis_url: str = "redis://localhost:6379/0"
    use_celery: bool = False

    rate_limit: str = "60/minute"

    # EmailJS — password reset emails
    emailjs_service_id: str = ""
    emailjs_template_id: str = ""
    emailjs_public_key: str = ""
    emailjs_private_key: str = ""
    password_reset_expire_minutes: int = 60

    @field_validator("deepgram_api_key", "gemini_api_key", "emailjs_private_key", mode="before")
    @classmethod
    def strip_api_keys(cls, value):
        return value.strip() if isinstance(value, str) else value

    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    def emailjs_configured(self) -> bool:
        return bool(
            self.emailjs_service_id.strip()
            and self.emailjs_template_id.strip()
            and self.emailjs_public_key.strip()
        )


def get_settings() -> Settings:
    return Settings()


class _SettingsProxy:
    def __getattr__(self, name: str):
        return getattr(get_settings(), name)


settings = _SettingsProxy()
