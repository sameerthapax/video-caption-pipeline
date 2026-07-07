from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.job import VideoJob


def fetch_job_or_404(*, db: Session, job_id: str, user_id: str) -> VideoJob:
    job = (
        db.query(VideoJob)
        .options(joinedload(VideoJob.result))
        .filter(VideoJob.id == job_id, VideoJob.user_id == user_id)
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


def fetch_result_or_raise(*, job: VideoJob):
    if job.result is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Result is not ready yet.")
    return job.result
