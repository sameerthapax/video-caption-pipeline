from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.job import VideoJob
from app.services.storage_service import (
    SignedUploadTarget,
    UploadedObjectMetadata,
    create_signed_upload_target,
    fetch_uploaded_object_metadata,
)

logger = logging.getLogger(__name__)

_FILENAME_SANITIZER = re.compile(r"[^A-Za-z0-9._-]+")


def prepare_video_upload(
    *,
    db: Session,
    filename: str,
    content_type: str,
    file_size: int,
    user_id: str,
) -> tuple[VideoJob, SignedUploadTarget]:
    normalized_filename = _normalize_filename(filename)
    logger.info(
        "Preparing upload for user %s: filename=%s content_type=%s file_size=%s",
        user_id,
        normalized_filename,
        content_type,
        file_size,
    )
    if file_size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size must be greater than 0.")

    if not content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only video uploads are supported.")

    job = VideoJob(
        user_id=user_id,
        original_filename=normalized_filename,
        storage_bucket=settings.supabase_storage_bucket,
        video_path="",
        upload_content_type=content_type,
        upload_file_size=file_size,
        status="pending_upload",
        current_step="awaiting_upload",
        progress=0,
    )
    db.add(job)
    db.flush()

    object_path = f"{user_id}/{job.id}/{normalized_filename}"
    job.video_path = object_path

    try:
        upload_target = create_signed_upload_target(
            bucket=job.storage_bucket,
            object_path=object_path,
            content_type=content_type,
        )
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    db.commit()
    db.refresh(job)
    logger.info(
        "Prepared signed upload for job %s in bucket %s at %s",
        job.id,
        job.storage_bucket,
        job.video_path,
    )
    return job, upload_target


def complete_video_upload(
    *,
    db: Session,
    job_id: str,
    object_path: str,
    file_size: int,
    content_type: str,
    user_id: str,
) -> tuple[VideoJob, UploadedObjectMetadata]:
    job, metadata = verify_video_upload(
        db=db,
        job_id=job_id,
        object_path=object_path,
        file_size=file_size,
        content_type=content_type,
        user_id=user_id,
    )
    update_video_job_state(
        db=db,
        job=job,
        status="uploaded",
        current_step="uploaded",
        progress=10,
    )
    return job, metadata


def verify_video_upload(
    *,
    db: Session,
    job_id: str,
    object_path: str,
    file_size: int,
    content_type: str,
    user_id: str,
) -> tuple[VideoJob, UploadedObjectMetadata]:
    logger.info(
        "Completing upload for job %s from user %s: object_path=%s content_type=%s file_size=%s",
        job_id,
        user_id,
        object_path,
        content_type,
        file_size,
    )
    job = db.query(VideoJob).filter(VideoJob.id == job_id, VideoJob.user_id == user_id).one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    if job.video_path != object_path:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Upload path does not match the prepared job.")

    if job.upload_file_size != file_size or job.upload_content_type != content_type:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload metadata does not match the prepared job.",
        )

    try:
        metadata = fetch_uploaded_object_metadata(bucket=job.storage_bucket, object_path=object_path)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if metadata is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Uploaded object was not found in storage.")

    _validate_uploaded_metadata(expected_job=job, actual_metadata=metadata)

    logger.info(
        "Verified storage upload for job %s in bucket %s at %s with metadata %s",
        job.id,
        metadata.bucket,
        metadata.object_path,
        metadata.metadata,
    )
    return job, metadata


def update_video_job_state(
    *,
    db: Session,
    job: VideoJob,
    status: str,
    current_step: str,
    progress: int,
    error_message: str | None = None,
) -> VideoJob:
    job.status = status
    job.current_step = current_step
    job.progress = progress
    if error_message is not None:
        job.error_message = error_message
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _normalize_filename(filename: str) -> str:
    basename = Path(filename).name.strip()
    if not basename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A video file name is required.")

    stem = Path(basename).stem or "upload"
    suffix = Path(basename).suffix.lower()
    sanitized_stem = _FILENAME_SANITIZER.sub("-", stem).strip("-.") or "upload"
    sanitized_suffix = _FILENAME_SANITIZER.sub("", suffix) or ".bin"
    return f"{sanitized_stem}{sanitized_suffix}"


def _validate_uploaded_metadata(*, expected_job: VideoJob, actual_metadata: UploadedObjectMetadata) -> None:
    if actual_metadata.size != expected_job.upload_file_size:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Uploaded file size did not match.")

    actual_content_type = actual_metadata.content_type
    if actual_content_type and actual_content_type != expected_job.upload_content_type:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Uploaded content type did not match.")
