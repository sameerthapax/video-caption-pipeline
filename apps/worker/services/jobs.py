from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.job import VideoJob
//

def claim_job_for_processing(*, db: Session, job_id: str) -> tuple[VideoJob | None, bool]:
    job = (
        db.execute(
            select(VideoJob)
            .where(VideoJob.id == job_id)
            .with_for_update(skip_locked=True)
        )
        .scalar_one_or_none()
    )
    if job is None:
        db.rollback()
        return None, False

    if job.status != "queued":
        db.rollback()
        return job, False

    job.status = "processing"
    job.current_step = "claimed"
    job.processing_started_at = datetime.now(timezone.utc)
    job.progress = 5
    job.error_message = ""
    db.add(job)
    db.commit()
    db.refresh(job)
    return job, True


def update_job_progress(
    *,
    db: Session,
    job: VideoJob,
    status: str | None = None,
    current_step: str | None = None,
    progress: int | None = None,
    error_message: str | None = None,
    preprocessing_metadata: dict[str, Any] | None = None,
) -> VideoJob:
    if status is not None:
        job.status = status
    if current_step is not None:
        job.current_step = current_step
    if progress is not None:
        job.progress = progress
    if error_message is not None:
        job.error_message = error_message
    if preprocessing_metadata is not None:
        existing_metadata = dict(job.preprocessing_metadata or {})
        existing_metadata.update(preprocessing_metadata)
        job.preprocessing_metadata = existing_metadata
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def refresh_job(*, db: Session, job_id: str) -> VideoJob | None:
    return db.get(VideoJob, job_id)
