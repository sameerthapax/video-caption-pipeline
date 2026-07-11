from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from core.database import SessionLocal
from models.job import VideoJob


def _use_dynamodb_status() -> bool:
    return os.environ.get("AWS_LAMBDA_JOB_STATUS_MODE") == "dynamodb"


def update_job_status(
    *,
    job_id: str,
    status: str | None = None,
    current_step: str | None = None,
    progress: int | None = None,
    error_message: str | None = None,
    artifact_paths: dict[str, Any] | None = None,
) -> VideoJob:
    if _use_dynamodb_status():
        _update_dynamodb_job_status(
            job_id=job_id,
            status=status,
            current_step=current_step,
            progress=progress,
            error_message=error_message,
            artifact_paths=artifact_paths,
        )
        return VideoJob(id=job_id)

    db: Session = SessionLocal()
    try:
        job = db.get(VideoJob, job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")
        if status is not None:
            job.status = status
        if current_step is not None:
            job.current_step = current_step
        if progress is not None:
            job.progress = progress
        if error_message is not None:
            job.error_message = error_message
        if artifact_paths is not None:
            existing = dict(job.artifact_paths or {})
            existing.update(artifact_paths)
            job.artifact_paths = existing
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    finally:
        db.close()


def _update_dynamodb_job_status(
    *,
    job_id: str,
    status: str | None,
    current_step: str | None,
    progress: int | None,
    error_message: str | None,
    artifact_paths: dict[str, Any] | None,
) -> None:
    import boto3

    table = boto3.resource("dynamodb").Table(os.environ["JOBS_TABLE"])
    fields: dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if status is not None:
        fields["status"] = status
    if current_step is not None:
        fields["current_step"] = current_step
    if progress is not None:
        fields["progress"] = progress
    if error_message is not None:
        fields["error_message"] = error_message
    if artifact_paths is not None:
        fields["artifact_paths"] = artifact_paths

    names: dict[str, str] = {}
    values: dict[str, Any] = {}
    assignments: list[str] = []
    for key, value in fields.items():
        names[f"#{key}"] = key
        values[f":{key}"] = _to_dynamodb_value(value)
        assignments.append(f"#{key} = :{key}")

    table.update_item(
        Key={"job_id": job_id},
        UpdateExpression="SET " + ", ".join(assignments),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


def _to_dynamodb_value(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _to_dynamodb_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_dynamodb_value(item) for item in value]
    return value
