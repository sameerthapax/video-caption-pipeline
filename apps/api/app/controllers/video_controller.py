from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser
from app.schemas.video import UploadResponse
from app.services.video_service import create_video_job


def upload_video(*, db: Session, video: UploadFile, user: AuthenticatedUser) -> UploadResponse:
    if not video.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A video file is required.")

    job = create_video_job(db=db, filename=video.filename, file_handle=video.file, user_id=user.id)
    return UploadResponse(job_id=job.id, status=job.status)
