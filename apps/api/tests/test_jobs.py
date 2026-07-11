from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.models.job import VideoCaptionResult, VideoJob


def test_status_returns_job(client):
    db = SessionLocal()
    job = VideoJob(
        user_id="test-user-id",
        original_filename="pending.mp4",
        storage_bucket="videos",
        video_path="videos/pending.mp4",
        upload_content_type="video/mp4",
        upload_file_size=1234,
        status="uploaded",
        current_step="uploaded",
        progress=5,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()

    response = client.get(f"/api/jobs/{job_id}/status/")

    assert response.status_code == 200
    assert response.json()["id"] == job_id


def test_result_returns_conflict_without_record(client):
    db = SessionLocal()
    job = VideoJob(
        user_id="test-user-id",
        original_filename="pending.mp4",
        storage_bucket="videos",
        video_path="videos/pending.mp4",
        upload_content_type="video/mp4",
        upload_file_size=1234,
        status="uploaded",
        current_step="uploaded",
        progress=5,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()

    response = client.get(f"/api/jobs/{job_id}/result/")

    assert response.status_code == 409


def test_result_returns_record_when_present(client):
    db = SessionLocal()
    job = VideoJob(
        user_id="test-user-id",
        original_filename="complete.mp4",
        storage_bucket="videos",
        video_path="videos/complete.mp4",
        upload_content_type="video/mp4",
        upload_file_size=1234,
        status="completed",
        current_step="completed",
        progress=100,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    db.add(
        VideoCaptionResult(
            job_id=job.id,
            neutral_summary="Summary",
            formal_caption="Formal",
            sarcastic_caption="Sarcastic",
            humorous_tech_caption="Tech",
            humorous_non_tech_caption="Non-tech",
            raw_output_json={"source": "test"},
        )
    )
    db.commit()
    job_id = job.id
    db.close()

    response = client.get(f"/api/jobs/{job_id}/result/")

    assert response.status_code == 200
    assert response.json()["formal_caption"] == "Formal"


def test_status_hides_other_users_jobs(client):
    db = SessionLocal()
    job = VideoJob(
        user_id="another-user-id",
        original_filename="hidden.mp4",
        storage_bucket="videos",
        video_path="videos/hidden.mp4",
        upload_content_type="video/mp4",
        upload_file_size=1234,
        status="uploaded",
        current_step="uploaded",
        progress=5,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()

    response = client.get(f"/api/jobs/{job_id}/status/")

    assert response.status_code == 404


def test_list_jobs_returns_latest_first_with_result_flag(client):
    db = SessionLocal()
    created_at = datetime.now(timezone.utc)
    older_job = VideoJob(
        user_id="test-user-id",
        original_filename="older.mp4",
        storage_bucket="videos",
        video_path="videos/older.mp4",
        upload_content_type="video/mp4",
        upload_file_size=1234,
        status="failed",
        current_step="processing_segment_4",
        progress=61,
        error_message="Worker failed",
        created_at=created_at,
        updated_at=created_at,
    )
    newer_job = VideoJob(
        user_id="test-user-id",
        original_filename="newer.mp4",
        storage_bucket="videos",
        video_path="videos/newer.mp4",
        upload_content_type="video/mp4",
        upload_file_size=2345,
        status="completed",
        current_step="completed",
        progress=100,
        created_at=created_at + timedelta(minutes=1),
        updated_at=created_at + timedelta(minutes=1),
    )
    db.add_all([older_job, newer_job])
    db.commit()
    db.refresh(older_job)
    db.refresh(newer_job)
    db.add(
        VideoCaptionResult(
            job_id=newer_job.id,
            neutral_summary="Summary",
            formal_caption="Formal",
            sarcastic_caption="Sarcastic",
            humorous_tech_caption="Tech",
            humorous_non_tech_caption="Non-tech",
            raw_output_json={"source": "test"},
        )
    )
    db.commit()
    db.close()

    response = client.get("/api/jobs/")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["original_filename"] == "newer.mp4"
    assert payload[0]["has_result"] is True
    assert payload[1]["has_result"] is False
