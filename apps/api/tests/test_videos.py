from pathlib import Path
import io

from app.core.auth import ACCESS_TOKEN_COOKIE, CSRF_COOKIE, CSRF_HEADER
from app.core.config import settings


def test_upload_creates_job(client, tmp_path: Path):
    original_media_root = settings.media_root
    settings.media_root = tmp_path
    settings.video_upload_root.mkdir(parents=True, exist_ok=True)
    client.cookies.set(ACCESS_TOKEN_COOKIE, "access-token")
    client.cookies.set(CSRF_COOKIE, "csrf-token")

    response = client.post(
        "/api/videos/upload/",
        headers={CSRF_HEADER: "csrf-token"},
        files={"video": ("clip.mp4", io.BytesIO(b"fake-video-bytes"), "video/mp4")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "uploaded"
    assert (tmp_path / "videos" / "clip.mp4").exists()

    settings.media_root = original_media_root


def test_upload_requires_csrf_header(client, tmp_path: Path):
    original_media_root = settings.media_root
    settings.media_root = tmp_path
    settings.video_upload_root.mkdir(parents=True, exist_ok=True)
    client.cookies.set(ACCESS_TOKEN_COOKIE, "access-token")
    client.cookies.set(CSRF_COOKIE, "csrf-token")

    response = client.post(
        "/api/videos/upload/",
        files={"video": ("clip.mp4", io.BytesIO(b"fake-video-bytes"), "video/mp4")},
    )

    assert response.status_code == 403

    settings.media_root = original_media_root
