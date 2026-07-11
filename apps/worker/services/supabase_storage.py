from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from storage.supabase import (
    StorageDownloadError,
    StorageUploadError,
    download_private_object,
    upload_private_object,
)

logger = logging.getLogger("video-caption-pipeline.worker")


def _use_s3_storage() -> bool:
    return os.environ.get("AWS_LAMBDA_STORAGE_MODE") == "s3"


def download_to_path(*, bucket: str, object_path: str, destination: Path) -> Path:
    if _use_s3_storage():
        logger.info("Downloading S3 object bucket=%s path=%s to %s", bucket, object_path, destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        _s3_client().download_file(bucket, object_path, str(destination))
        return destination
    logger.info("Downloading Supabase object bucket=%s path=%s to %s", bucket, object_path, destination)
    download_private_object(bucket=bucket, object_path=object_path, destination=destination)
    return destination


def try_download_to_path(*, bucket: str, object_path: str, destination: Path) -> Path | None:
    try:
        return download_to_path(bucket=bucket, object_path=object_path, destination=destination)
    except StorageDownloadError:
        logger.warning("Optional object missing bucket=%s path=%s", bucket, object_path)
        return None
    except Exception as exc:
        if _use_s3_storage() and _is_missing_s3_object_error(exc):
            logger.warning("Optional S3 object missing bucket=%s path=%s", bucket, object_path)
            return None
        raise


def upload_file(*, bucket: str, object_path: str, source: Path, content_type: str) -> str:
    if _use_s3_storage():
        logger.info("Uploading S3 artifact bucket=%s path=%s from %s", bucket, object_path, source)
        _s3_client().upload_file(
            str(source),
            bucket,
            object_path,
            ExtraArgs={"ContentType": content_type, "ServerSideEncryption": "AES256"},
        )
        return object_path
    logger.info("Uploading artifact bucket=%s path=%s from %s", bucket, object_path, source)
    upload_private_object(bucket=bucket, object_path=object_path, source=source, content_type=content_type)
    return object_path


def upload_json(*, bucket: str, object_path: str, payload: dict) -> str:
    temp_path = Path("/tmp") / f"{Path(object_path).name}"
    temp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        return upload_file(bucket=bucket, object_path=object_path, source=temp_path, content_type="application/json")
    finally:
        temp_path.unlink(missing_ok=True)


async def upload_file_async(*, bucket: str, object_path: str, source: Path, content_type: str) -> str:
    return await asyncio.to_thread(
        upload_file,
        bucket=bucket,
        object_path=object_path,
        source=source,
        content_type=content_type,
    )


def _s3_client():
    import boto3

    return boto3.client("s3")


def _is_missing_s3_object_error(exc: Exception) -> bool:
    response = getattr(exc, "response", {})
    return response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}


__all__ = [
    "StorageDownloadError",
    "StorageUploadError",
    "download_to_path",
    "try_download_to_path",
    "upload_file",
    "upload_file_async",
    "upload_json",
]
