import logging
from collections.abc import AsyncIterator

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.auth import AuthenticatedUser
from app.schemas.video import (
    UploadCompletionRequest,
    UploadCompletionResponse,
    UploadPreparationRequest,
    UploadPreparationResponse,
)
from app.services.video_service import (
    complete_video_upload,
    prepare_video_upload,
    update_video_job_state,
    verify_video_upload,
)
from app.services.worker_invoker import invoke_video_worker
from app.utils.sse import format_sse, format_sse_comment

logger = logging.getLogger(__name__)


def prepare_upload(
    *,
    db: Session,
    payload: UploadPreparationRequest,
    user: AuthenticatedUser,
) -> UploadPreparationResponse:
    logger.info(
        "Received upload preparation request from user %s for filename=%s content_type=%s file_size=%s",
        user.id,
        payload.filename,
        payload.content_type,
        payload.file_size,
    )
    job, upload_target = prepare_video_upload(
        db=db,
        filename=payload.filename,
        content_type=payload.content_type,
        file_size=payload.file_size,
        user_id=user.id,
    )
    return UploadPreparationResponse(
        job_id=job.id,
        status=job.status,
        bucket=upload_target.bucket,
        object_path=upload_target.object_path,
        upload_url=upload_target.upload_url,
        upload_method="PUT",
        upload_headers=upload_target.upload_headers,
    )


def complete_upload(
    *,
    db: Session,
    payload: UploadCompletionRequest,
    user: AuthenticatedUser,
) -> UploadCompletionResponse:
    logger.info(
        "Received upload completion callback from user %s for job %s and object_path=%s",
        user.id,
        payload.job_id,
        payload.object_path,
    )
    job, _ = complete_video_upload(
        db=db,
        job_id=payload.job_id,
        object_path=payload.object_path,
        file_size=payload.file_size,
        content_type=payload.content_type,
        user_id=user.id,
    )
    return UploadCompletionResponse(job_id=job.id, status=job.status, verified=True)


async def stream_complete_upload(
    *,
    db: Session,
    payload: UploadCompletionRequest,
    user: AuthenticatedUser,
) -> AsyncIterator[str]:
    logger.info(
        "Received streaming upload completion callback from user %s for job %s and object_path=%s",
        user.id,
        payload.job_id,
        payload.object_path,
    )
    job = None
    try:
        job, _ = verify_video_upload(
            db=db,
            job_id=payload.job_id,
            object_path=payload.object_path,
            file_size=payload.file_size,
            content_type=payload.content_type,
            user_id=user.id,
        )
        update_video_job_state(
            db=db,
            job=job,
            status="queued",
            current_step="queued",
            progress=15,
            error_message="",
        )
        yield format_sse(
            event="queued",
            data={
                "event": "queued",
                "job_id": job.id,
                "step": "queued",
                "message": "Upload verified and job queued.",
                "progress": 15,
            },
        )

        yield format_sse_comment("worker invocation started")
        yield format_sse(
            event="worker_invoked",
            data={
                "event": "worker_invoked",
                "job_id": job.id,
                "step": "worker_invocation",
                "message": "Worker invocation accepted.",
                "progress": 20,
            },
        )

        async for worker_event in invoke_video_worker(job.id):
            yield format_sse(event=worker_event.event, data=worker_event.to_dict())
    except HTTPException as exc:
        logger.warning("Streaming upload completion rejected for job %s: %s", payload.job_id, exc.detail)
        if job is not None:
            update_video_job_state(
                db=db,
                job=job,
                status="failed",
                current_step="upload_validation_failed",
                progress=0,
                error_message=str(exc.detail),
            )
        yield format_sse(
            event="failed",
            data={
                "event": "failed",
                "job_id": payload.job_id,
                "step": "upload_validation_failed",
                "message": str(exc.detail),
                "progress": 0,
            },
        )
    except Exception as exc:
        logger.exception("Streaming upload completion failed for job %s", payload.job_id)
        if job is not None:
            update_video_job_state(
                db=db,
                job=job,
                status="failed",
                current_step="worker_failed",
                progress=0,
                error_message="Worker invocation failed.",
            )
        yield format_sse(
            event="failed",
            data={
                "event": "failed",
                "job_id": payload.job_id,
                "step": "worker_failed",
                "message": "Worker invocation failed.",
                "progress": 0,
            },
        )
