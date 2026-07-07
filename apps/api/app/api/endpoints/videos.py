from fastapi import APIRouter, Depends, File, status, UploadFile
from sqlalchemy.orm import Session

from app.controllers.video_controller import upload_video
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.schemas.video import UploadResponse

router = APIRouter()


@router.post("/upload/", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_video_endpoint(
    video: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> UploadResponse:
    return upload_video(db=db, video=video, user=user)
