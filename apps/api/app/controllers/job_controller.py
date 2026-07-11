from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser
from app.schemas.job import CaptionResultResponse, JobListItemResponse, VideoJobStatusResponse
from app.services.job_service import fetch_job_or_404, fetch_result_or_raise, list_jobs_for_user


def get_job_status(*, db: Session, job_id: str, user: AuthenticatedUser) -> VideoJobStatusResponse:
    job = fetch_job_or_404(db=db, job_id=job_id, user_id=user.id)
    return VideoJobStatusResponse.model_validate(job)


def get_job_result(*, db: Session, job_id: str, user: AuthenticatedUser) -> CaptionResultResponse:
    job = fetch_job_or_404(db=db, job_id=job_id, user_id=user.id)
    result = fetch_result_or_raise(job=job)
    return CaptionResultResponse.model_validate(result)


def list_jobs(*, db: Session, user: AuthenticatedUser) -> list[JobListItemResponse]:
    jobs = list_jobs_for_user(db=db, user_id=user.id)
    return [
        JobListItemResponse(
            id=job.id,
            status=job.status,
            current_step=job.current_step,
            progress=job.progress,
            error_message=job.error_message,
            original_filename=job.original_filename,
            created_at=job.created_at,
            updated_at=job.updated_at,
            has_result=job.result is not None,
        )
        for job in jobs
    ]
