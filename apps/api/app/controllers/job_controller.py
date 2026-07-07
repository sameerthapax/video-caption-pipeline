from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser
from app.schemas.job import CaptionResultResponse, VideoJobStatusResponse
from app.services.job_service import fetch_job_or_404, fetch_result_or_raise


def get_job_status(*, db: Session, job_id: str, user: AuthenticatedUser) -> VideoJobStatusResponse:
    job = fetch_job_or_404(db=db, job_id=job_id, user_id=user.id)
    return VideoJobStatusResponse.model_validate(job)


def get_job_result(*, db: Session, job_id: str, user: AuthenticatedUser) -> CaptionResultResponse:
    job = fetch_job_or_404(db=db, job_id=job_id, user_id=user.id)
    result = fetch_result_or_raise(job=job)
    return CaptionResultResponse.model_validate(result)
