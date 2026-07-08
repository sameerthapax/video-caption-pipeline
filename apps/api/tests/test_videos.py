from app.core.auth import ACCESS_TOKEN_COOKIE, CSRF_COOKIE, CSRF_HEADER
from app.core.database import SessionLocal
from app.models.job import VideoJob
from app.services.storage_service import SignedUploadTarget, UploadedObjectMetadata, _normalize_signed_upload_url
from app.services.worker_invoker import WorkerProgressEvent
from app.services import video_service


def test_prepare_upload_creates_pending_job_and_returns_signed_url(client, monkeypatch):
    def fake_create_signed_upload_target(*, bucket: str, object_path: str, content_type: str) -> SignedUploadTarget:
        assert bucket == "videos"
        assert object_path.endswith("/clip.mp4")
        assert content_type == "video/mp4"
        return SignedUploadTarget(
            bucket=bucket,
            object_path=object_path,
            upload_url=f"http://storage.local/{object_path}",
            upload_headers={"Content-Type": content_type},
        )

    monkeypatch.setattr(video_service, "create_signed_upload_target", fake_create_signed_upload_target)

    client.cookies.set(ACCESS_TOKEN_COOKIE, "access-token")
    client.cookies.set(CSRF_COOKIE, "csrf-token")
    response = client.post(
        "/api/videos/upload/",
        headers={CSRF_HEADER: "csrf-token"},
        json={"filename": "clip.mp4", "content_type": "video/mp4", "file_size": 2048},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "pending_upload"
    assert payload["bucket"] == "videos"
    assert payload["upload_method"] == "PUT"
    assert payload["upload_url"].endswith(".mp4")

    db = SessionLocal()
    job = db.query(VideoJob).filter(VideoJob.id == payload["job_id"]).one()
    assert job.video_path == payload["object_path"]
    assert job.upload_file_size == 2048
    assert job.upload_content_type == "video/mp4"
    assert job.status == "pending_upload"
    db.close()


def test_complete_upload_verifies_metadata_and_marks_job_uploaded(client, monkeypatch):
    db = SessionLocal()
    job = VideoJob(
        user_id="test-user-id",
        original_filename="clip.mp4",
        storage_bucket="videos",
        video_path="test-user-id/job-123/clip.mp4",
        upload_content_type="video/mp4",
        upload_file_size=2048,
        status="pending_upload",
        current_step="awaiting_upload",
        progress=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    object_path = job.video_path
    db.close()

    def fake_fetch_uploaded_object_metadata(*, bucket: str, object_path: str) -> UploadedObjectMetadata | None:
        return UploadedObjectMetadata(
            bucket=bucket,
            object_path=object_path,
            metadata={"size": 2048, "mimetype": "video/mp4"},
            size=2048,
            content_type="video/mp4",
        )

    monkeypatch.setattr(video_service, "fetch_uploaded_object_metadata", fake_fetch_uploaded_object_metadata)

    client.cookies.set(ACCESS_TOKEN_COOKIE, "access-token")
    client.cookies.set(CSRF_COOKIE, "csrf-token")
    response = client.post(
        "/api/videos/upload/complete/",
        headers={CSRF_HEADER: "csrf-token"},
        json={
            "job_id": job_id,
            "object_path": object_path,
            "file_size": 2048,
            "content_type": "video/mp4",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"job_id": job_id, "status": "uploaded", "verified": True}

    db = SessionLocal()
    refreshed_job = db.query(VideoJob).filter(VideoJob.id == job_id).one()
    assert refreshed_job.status == "uploaded"
    assert refreshed_job.current_step == "uploaded"
    assert refreshed_job.progress == 10
    db.close()


def test_complete_upload_rejects_metadata_mismatch(client, monkeypatch):
    db = SessionLocal()
    job = VideoJob(
        user_id="test-user-id",
        original_filename="clip.mp4",
        storage_bucket="videos",
        video_path="test-user-id/job-456/clip.mp4",
        upload_content_type="video/mp4",
        upload_file_size=2048,
        status="pending_upload",
        current_step="awaiting_upload",
        progress=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    object_path = job.video_path
    db.close()

    def fake_fetch_uploaded_object_metadata(*, bucket: str, object_path: str) -> UploadedObjectMetadata | None:
        return UploadedObjectMetadata(
            bucket=bucket,
            object_path=object_path,
            metadata={"size": 1024, "mimetype": "video/mp4"},
            size=1024,
            content_type="video/mp4",
        )

    monkeypatch.setattr(video_service, "fetch_uploaded_object_metadata", fake_fetch_uploaded_object_metadata)

    client.cookies.set(ACCESS_TOKEN_COOKIE, "access-token")
    client.cookies.set(CSRF_COOKIE, "csrf-token")
    response = client.post(
        "/api/videos/upload/complete/",
        headers={CSRF_HEADER: "csrf-token"},
        json={
            "job_id": job_id,
            "object_path": object_path,
            "file_size": 2048,
            "content_type": "video/mp4",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Uploaded file size did not match."


def test_complete_upload_stream_marks_job_queued_and_streams_worker_events(client, monkeypatch):
    db = SessionLocal()
    job = VideoJob(
        user_id="test-user-id",
        original_filename="clip.mp4",
        storage_bucket="videos",
        video_path="test-user-id/job-stream/clip.mp4",
        upload_content_type="video/mp4",
        upload_file_size=2048,
        status="pending_upload",
        current_step="awaiting_upload",
        progress=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    object_path = job.video_path
    db.close()

    def fake_fetch_uploaded_object_metadata(*, bucket: str, object_path: str) -> UploadedObjectMetadata | None:
        return UploadedObjectMetadata(
            bucket=bucket,
            object_path=object_path,
            metadata={"size": 2048, "mimetype": "video/mp4"},
            size=2048,
            content_type="video/mp4",
        )

    async def fake_invoke_video_worker(job_id: str):
        yield WorkerProgressEvent(
            event="claimed",
            job_id=job_id,
            step="claimed",
            message="Worker claimed the queued job.",
            progress=5,
        )
        yield WorkerProgressEvent(
            event="preprocessing_completed",
            job_id=job_id,
            step="preprocessing_completed",
            message="Preprocessing completed.",
            progress=95,
        )

    monkeypatch.setattr(video_service, "fetch_uploaded_object_metadata", fake_fetch_uploaded_object_metadata)
    monkeypatch.setattr("app.controllers.video_controller.invoke_video_worker", fake_invoke_video_worker)

    client.cookies.set(ACCESS_TOKEN_COOKIE, "access-token")
    client.cookies.set(CSRF_COOKIE, "csrf-token")
    response = client.post(
        "/api/videos/upload/complete/stream",
        headers={CSRF_HEADER: "csrf-token"},
        json={
            "job_id": job_id,
            "object_path": object_path,
            "file_size": 2048,
            "content_type": "video/mp4",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: queued" in response.text
    assert "event: worker_invoked" in response.text
    assert "event: claimed" in response.text
    assert "event: preprocessing_completed" in response.text

    db = SessionLocal()
    refreshed_job = db.query(VideoJob).filter(VideoJob.id == job_id).one()
    assert refreshed_job.status == "queued"
    assert refreshed_job.current_step == "queued"
    assert refreshed_job.progress == 15
    db.close()


def test_prepare_upload_rejects_non_video_content_type(client):
    client.cookies.set(ACCESS_TOKEN_COOKIE, "access-token")
    client.cookies.set(CSRF_COOKIE, "csrf-token")
    response = client.post(
        "/api/videos/upload/",
        headers={CSRF_HEADER: "csrf-token"},
        json={"filename": "clip.png", "content_type": "image/png", "file_size": 2048},
    )

    assert response.status_code == 422
    assert "Unsupported video file extension." in response.text


def test_prepare_upload_rejects_oversized_file(client):
    client.cookies.set(ACCESS_TOKEN_COOKIE, "access-token")
    client.cookies.set(CSRF_COOKIE, "csrf-token")
    response = client.post(
        "/api/videos/upload/",
        headers={CSRF_HEADER: "csrf-token"},
        json={"filename": "clip.mp4", "content_type": "video/mp4", "file_size": 60 * 1024 * 1024},
    )

    assert response.status_code == 422


def test_normalize_signed_upload_url_prefixes_storage_api_path():
    normalized = _normalize_signed_upload_url("/object/upload/sign/videos/test/debug.mp4?token=abc")
    assert normalized == "http://localhost:54321/storage/v1/object/upload/sign/videos/test/debug.mp4?token=abc"


def test_prepare_upload_accepts_common_video_mime_variant(client, monkeypatch):
    def fake_create_signed_upload_target(*, bucket: str, object_path: str, content_type: str) -> SignedUploadTarget:
        assert content_type == "video/x-m4v"
        return SignedUploadTarget(
            bucket=bucket,
            object_path=object_path,
            upload_url=f"http://storage.local/{object_path}",
            upload_headers={"Content-Type": content_type},
        )

    monkeypatch.setattr(video_service, "create_signed_upload_target", fake_create_signed_upload_target)

    client.cookies.set(ACCESS_TOKEN_COOKIE, "access-token")
    client.cookies.set(CSRF_COOKIE, "csrf-token")
    response = client.post(
        "/api/videos/upload/",
        headers={CSRF_HEADER: "csrf-token"},
        json={"filename": "clip.m4v", "content_type": "video/x-m4v", "file_size": 2048},
    )

    assert response.status_code == 202
