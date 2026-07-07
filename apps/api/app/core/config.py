from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[4] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "video-caption-pipeline-api"
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_force_https: bool = Field(default=False, alias="APP_FORCE_HTTPS")
    database_url: str = Field(alias="DATABASE_URL")
    cors_allowed_origins: str = Field(default="http://localhost:5173", alias="CORS_ALLOWED_ORIGINS")
    allowed_hosts_raw: str = Field(default="localhost,127.0.0.1,0.0.0.0,testserver", alias="ALLOWED_HOSTS")
    supabase_url: str | None = Field(default=None, alias="SUPABASE_URL")
    supabase_anon_key: str | None = Field(default=None, alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str | None = Field(default=None, alias="SUPABASE_SERVICE_ROLE_KEY")
    redis_url: str = Field(default="redis://127.0.0.1:6379/0", alias="REDIS_URL")
    redis_key_prefix: str = Field(default="video-caption-pipeline", alias="REDIS_KEY_PREFIX")
    auth_rate_limit_window_seconds: int = Field(default=60, alias="AUTH_RATE_LIMIT_WINDOW_SECONDS")
    auth_rate_limit_max_requests: int = Field(default=10, alias="AUTH_RATE_LIMIT_MAX_REQUESTS")
    upload_rate_limit_window_seconds: int = Field(default=60, alias="UPLOAD_RATE_LIMIT_WINDOW_SECONDS")
    upload_rate_limit_max_requests: int = Field(default=20, alias="UPLOAD_RATE_LIMIT_MAX_REQUESTS")
    media_root: Path = Path(__file__).resolve().parents[2] / "media"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @property
    def allowed_hosts(self) -> list[str]:
        return [host.strip() for host in self.allowed_hosts_raw.split(",") if host.strip()]

    @property
    def video_upload_root(self) -> Path:
        return self.media_root / "videos"


settings = Settings()
