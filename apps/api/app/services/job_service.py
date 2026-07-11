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


def list_jobs_for_user(*, db: Session, user_id: str, limit: int = 20) -> list[VideoJob]:
    return (
        db.query(VideoJob)
        .options(joinedload(VideoJob.result))
        .filter(VideoJob.user_id == user_id)
        .order_by(VideoJob.created_at.desc())
        .limit(limit)
        .all()
    )


def summarize_jobs_for_user(*, db: Session, user_id: str) -> dict[str, object]:
    jobs = (
        db.query(VideoJob)
        .filter(VideoJob.user_id == user_id)
        .order_by(VideoJob.created_at.desc())
        .all()
    )
    total_jobs = len(jobs)
    completed_jobs = sum(1 for job in jobs if job.status == "completed")
    failed_jobs = sum(1 for job in jobs if job.status == "failed")
    active_jobs = sum(1 for job in jobs if job.status in {"pending_upload", "uploaded", "queued", "processing"})

    return {
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "active_jobs": active_jobs,
        "latest_job_at": jobs[0].created_at if jobs else None,
    }
