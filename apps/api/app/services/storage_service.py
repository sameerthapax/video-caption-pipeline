from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urljoin

import httpx
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine


@dataclass(frozen=True)
class SignedUploadTarget:
    bucket: str
    object_path: str
    upload_url: str
    upload_headers: dict[str, str]


@dataclass(frozen=True)
class UploadedObjectMetadata:
    bucket: str
    object_path: str
    metadata: dict[str, Any]
    size: int | None
    content_type: str | None


def assert_storage_is_configured() -> None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Supabase Storage is not configured.")


def create_signed_upload_target(*, bucket: str, object_path: str, content_type: str) -> SignedUploadTarget:
    assert_storage_is_configured()
    encoded_path = quote(object_path, safe="/")
    endpoint = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/upload/sign/{bucket}/{encoded_path}"
    headers = _service_role_headers()

    with httpx.Client(timeout=10.0) as client:
        response = client.post(endpoint, headers=headers, json={"upsert": False})
    payload = _parse_storage_response(response)

    signed_url = payload.get("signedURL") or payload.get("signedUrl") or payload.get("url")
    token = payload.get("token")
    if isinstance(signed_url, str) and signed_url:
        upload_url = _normalize_signed_upload_url(signed_url)
    elif isinstance(token, str) and token:
        upload_url = (
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/upload/sign/"
            f"{bucket}/{encoded_path}?token={quote(token, safe='')}"
        )
    else:
        raise RuntimeError("Supabase Storage did not return a usable signed upload URL.")

    return SignedUploadTarget(
        bucket=bucket,
        object_path=object_path,
        upload_url=upload_url,
        upload_headers={"Content-Type": content_type},
    )


def fetch_uploaded_object_metadata(*, bucket: str, object_path: str) -> UploadedObjectMetadata | None:
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Storage verification requires a PostgreSQL database connection.")

    with engine.begin() as connection:
        row = (
            connection.execute(
                text(
                    """
                    select bucket_id, name, metadata
                    from storage.objects
                    where bucket_id = :bucket and name = :name
                    limit 1
                    """
                ),
                {"bucket": bucket, "name": object_path},
            )
            .mappings()
            .first()
        )

    if row is None:
        return None

    metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    return UploadedObjectMetadata(
        bucket=row.get("bucket_id", bucket),
        object_path=row.get("name", object_path),
        metadata=metadata,
        size=_coerce_size(metadata),
        content_type=_coerce_content_type(metadata),
    )


def _service_role_headers() -> dict[str, str]:
    service_role_key = settings.supabase_service_role_key
    assert service_role_key is not None
    return {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }


def _normalize_signed_upload_url(signed_url: str) -> str:
    if signed_url.startswith("http"):
        return signed_url

    normalized_base = settings.supabase_url.rstrip("/")
    if signed_url.startswith("/storage/v1/"):
        return f"{normalized_base}{signed_url}"

    if signed_url.startswith("/object/"):
        return f"{normalized_base}/storage/v1{signed_url}"

    return urljoin(f"{normalized_base}/storage/v1/", signed_url.lstrip("/"))


def _parse_storage_response(response: httpx.Response) -> Any:
    if response.is_success:
        return response.json()

    detail = response.text
    try:
        payload = response.json()
    except ValueError:
        payload = None

    if isinstance(payload, dict):
        detail = str(payload.get("message") or payload.get("error") or payload.get("msg") or detail)

    raise RuntimeError(detail or f"Supabase Storage request failed with status {response.status_code}.")


def _coerce_size(metadata: dict[str, Any]) -> int | None:
    for key in ("size", "fileSize", "contentLength"):
        value = metadata.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def _coerce_content_type(metadata: dict[str, Any]) -> str | None:
    for key in ("mimetype", "contentType"):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return None
