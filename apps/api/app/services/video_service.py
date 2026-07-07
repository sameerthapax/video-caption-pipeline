from io import BufferedReader
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.job import VideoJob
from app.utils.files import build_unique_destination, copy_upload_to_path


def create_video_job(*, db: Session, filename: str, file_handle: BufferedReader, user_id: str) -> VideoJob:
    settings.video_upload_root.mkdir(parents=True, exist_ok=True)
    destination = build_unique_destination(settings.video_upload_root, filename)
    copy_upload_to_path(file_handle=file_handle, destination=destination)

    job = VideoJob(
        user_id=user_id,
        original_filename=filename,
        video_path=str(destination.relative_to(settings.media_root)),
        status="uploaded",
        current_step="uploaded",
        progress=5,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
