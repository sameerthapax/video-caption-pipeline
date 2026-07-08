from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import httpx

from core.config import settings


class StorageDownloadError(RuntimeError):
    pass


class StorageUploadError(RuntimeError):
    pass


def download_private_object(*, bucket: str, object_path: str, destination: Path) -> None:
    encoded_path = quote(object_path, safe="/")
    endpoint = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{encoded_path}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }

    destination.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", endpoint, headers=headers, timeout=60.0) as response:
        if response.status_code >= 400:
            raise StorageDownloadError(response.text or "Failed to download video from Supabase Storage.")
        with destination.open("wb") as file_handle:
            for chunk in response.iter_bytes():
                file_handle.write(chunk)


def upload_private_object(*, bucket: str, object_path: str, source: Path, content_type: str) -> None:
    encoded_path = quote(object_path, safe="/")
    endpoint = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{encoded_path}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    with source.open("rb") as file_handle:
        response = httpx.post(endpoint, headers=headers, content=file_handle.read(), timeout=60.0)

    if response.status_code >= 400:
        raise StorageUploadError(response.text or "Failed to upload processed artifact to Supabase Storage.")
