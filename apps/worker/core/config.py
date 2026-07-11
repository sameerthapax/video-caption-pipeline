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
    frame_extract_width: int = Field(default=640, alias="FRAME_EXTRACT_WIDTH")
    debug_keep_temp: bool = Field(default=False, alias="DEBUG_KEEP_TEMP")
    google_gemini_api_key: str | None = Field(default=None, alias="GOOGLE_GEMINI_API_KEY")
    google_gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com",
        alias="GOOGLE_GEMINI_BASE_URL",
    )
    google_gemini_transcription_model: str = Field(
        default="gemini-3.5-flash",
        alias="GOOGLE_GEMINI_TRANSCRIPTION_MODEL",
    )
    google_gemini_timeout_seconds: int = Field(default=60, alias="GOOGLE_GEMINI_TIMEOUT_SECONDS")
    fireworks_api_key: str | None = Field(default=None, alias="FIREWORKS_API_KEY")
    fireworks_base_url: str = Field(default="https://api.fireworks.ai/inference/v1", alias="FIREWORKS_BASE_URL")
    fireworks_model: str | None = Field(default=None, alias="FIREWORKS_MODEL")
    fireworks_timeout_seconds: int = Field(default=90, alias="FIREWORKS_TIMEOUT_SECONDS")
    fireworks_max_retries: int = Field(default=3, alias="FIREWORKS_MAX_RETRIES")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_final_caption_model: str = Field(default="gpt-5.5", alias="OPENAI_FINAL_CAPTION_MODEL")
    openai_timeout_seconds: int = Field(default=90, alias="OPENAI_TIMEOUT_SECONDS")
    openai_max_retries: int = Field(default=3, alias="OPENAI_MAX_RETRIES")
    openai_reasoning_effort: str = Field(default="medium", alias="OPENAI_REASONING_EFFORT")
    openai_text_verbosity: str = Field(default="medium", alias="OPENAI_TEXT_VERBOSITY")


settings = Settings()
