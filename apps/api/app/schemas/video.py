from typing import Literal

from pydantic import BaseModel


VideoJobStatus = Literal["uploaded", "processing", "completed", "failed"]


class UploadResponse(BaseModel):
    job_id: str
    status: VideoJobStatus
