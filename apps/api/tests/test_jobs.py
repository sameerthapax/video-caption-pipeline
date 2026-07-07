from app.core.database import SessionLocal
from app.models.job import VideoCaptionResult, VideoJob


def test_status_returns_job(client):
    db = SessionLocal()
    job = VideoJob(
        user_id="test-user-id",
        original_filename="pending.mp4",
        video_path="videos/pending.mp4",
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
        video_path="videos/pending.mp4",
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
        video_path="videos/complete.mp4",
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
        video_path="videos/hidden.mp4",
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
