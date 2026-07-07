from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_VIDEO_UPLOAD_BYTES = 50 * 1024 * 1024
ALLOWED_VIDEO_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
    "video/x-m4v",
    "application/octet-stream",
}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}


VideoJobStatus = Literal["pending_upload", "uploaded", "queued", "processing", "completed", "failed"]


class UploadPreparationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=255)
    file_size: int = Field(gt=0, le=MAX_VIDEO_UPLOAD_BYTES)

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        extension = Path(value).suffix.lower()
        if extension not in ALLOWED_VIDEO_EXTENSIONS:
            raise ValueError("Unsupported video file extension.")
        return value

    @field_validator("content_type", mode="after")
    @classmethod
    def validate_content_type(cls, value: str, info) -> str:
        filename = str(info.data.get("filename", ""))
        extension = Path(filename).suffix.lower()
        if value in ALLOWED_VIDEO_CONTENT_TYPES and extension in ALLOWED_VIDEO_EXTENSIONS:
            return value
        if value.startswith("video/") and extension in ALLOWED_VIDEO_EXTENSIONS:
            return value
        if value == "application/octet-stream" and extension in ALLOWED_VIDEO_EXTENSIONS:
            return value
        if value not in ALLOWED_VIDEO_CONTENT_TYPES:
            raise ValueError("Unsupported video content type.")
        return value


class UploadPreparationResponse(BaseModel):
    job_id: str
    status: VideoJobStatus
    bucket: str
    object_path: str
    upload_url: str
    upload_method: Literal["PUT"]
    upload_headers: dict[str, str]


class UploadCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    job_id: str = Field(min_length=1, max_length=36)
    object_path: str = Field(min_length=1, max_length=500)
    file_size: int = Field(gt=0, le=MAX_VIDEO_UPLOAD_BYTES)
    content_type: str = Field(min_length=1, max_length=255)

    @field_validator("content_type", mode="after")
    @classmethod
    def validate_completion_content_type(cls, value: str) -> str:
        if value not in ALLOWED_VIDEO_CONTENT_TYPES and not value.startswith("video/"):
            raise ValueError("Unsupported video content type.")
        return value


class UploadCompletionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    status: VideoJobStatus
    verified: bool
