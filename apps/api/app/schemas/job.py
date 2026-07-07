from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


VideoJobStatus = Literal["pending_upload", "uploaded", "queued", "processing", "completed", "failed"]


class VideoJobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: VideoJobStatus
    current_step: str
    progress: int
    error_message: str
    original_filename: str
    created_at: datetime
    updated_at: datetime


class CaptionResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    neutral_summary: str
    formal_caption: str
    sarcastic_caption: str
    humorous_tech_caption: str
    humorous_non_tech_caption: str
    raw_output_json: dict[str, Any]
    created_at: datetime
