from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.job_controller import get_job_result, get_job_status, list_jobs
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.schemas.job import CaptionResultResponse, JobListItemResponse, VideoJobStatusResponse

router = APIRouter()


@router.get("/", response_model=list[JobListItemResponse])
def list_jobs_endpoint(
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> list[JobListItemResponse]:
    return list_jobs(db=db, user=user)


@router.get("/{job_id}/status/", response_model=VideoJobStatusResponse)
def get_job_status_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> VideoJobStatusResponse:
    return get_job_status(db=db, job_id=job_id, user=user)


@router.get("/{job_id}/result/", response_model=CaptionResultResponse)
def get_job_result_endpoint(
    job_id: str,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CaptionResultResponse:
    return get_job_result(db=db, job_id=job_id, user=user)
