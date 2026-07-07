from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.controllers.video_controller import complete_upload, prepare_upload, stream_complete_upload
from app.core.auth import AuthenticatedUser, get_current_user
from app.core.database import get_db
from app.schemas.video import (
    UploadCompletionRequest,
    UploadCompletionResponse,
    UploadPreparationRequest,
    UploadPreparationResponse,
)

router = APIRouter()


@router.post("/upload/", response_model=UploadPreparationResponse, status_code=status.HTTP_202_ACCEPTED)
def prepare_video_upload_endpoint(
    payload: UploadPreparationRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> UploadPreparationResponse:
    return prepare_upload(db=db, payload=payload, user=user)


@router.post("/upload/complete/", response_model=UploadCompletionResponse, status_code=status.HTTP_200_OK)
def complete_video_upload_endpoint(
    payload: UploadCompletionRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> UploadCompletionResponse:
    return complete_upload(db=db, payload=payload, user=user)


@router.post("/upload/complete/stream", status_code=status.HTTP_200_OK)
async def complete_video_upload_stream_endpoint(
    payload: UploadCompletionRequest,
    db: Session = Depends(get_db),
    user: AuthenticatedUser = Depends(get_current_user),
) -> StreamingResponse:
    return StreamingResponse(
        stream_complete_upload(db=db, payload=payload, user=user),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
