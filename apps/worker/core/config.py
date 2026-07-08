from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[3] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "video-caption-pipeline-worker"
    database_url: str = Field(alias="DATABASE_URL")
    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_service_role_key: str = Field(alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_video_bucket: str = Field(default="videos", alias="SUPABASE_VIDEO_BUCKET")
    max_video_size_mb: int = Field(default=500, alias="MAX_VIDEO_SIZE_MB")
    max_video_duration_seconds: int = Field(default=180, alias="MAX_VIDEO_DURATION_SECONDS")
    worker_tmp_root: str = Field(default="/tmp/video-jobs", alias="WORKER_TMP_ROOT")
    ffmpeg_path: str = Field(default="ffmpeg", alias="FFMPEG_PATH")
    ffprobe_path: str = Field(default="ffprobe", alias="FFPROBE_PATH")
    ffmpeg_timeout_seconds: int = Field(default=300, alias="FFMPEG_TIMEOUT_SECONDS")
    ffprobe_timeout_seconds: int = Field(default=60, alias="FFPROBE_TIMEOUT_SECONDS")


settings = Settings()
