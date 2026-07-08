from models.job import VideoJob
from services.jobs import claim_job_for_processing


def test_claim_rejects_non_queued_job():
    from core.database import SessionLocal

    db = SessionLocal()
    job = VideoJob(
        id="job-1",
        user_id="user-1",
        original_filename="clip.mp4",
        storage_bucket="videos",
        video_path="user-1/job-1/clip.mp4",
        upload_content_type="video/mp4",
        upload_file_size=123,
        status="processing",
        current_step="claimed",
        progress=5,
    )
    db.add(job)
    db.commit()
    db.close()

    db = SessionLocal()
    claimed_job, claimed = claim_job_for_processing(db=db, job_id="job-1")
    assert claimed_job is not None
    assert claimed is False
    assert claimed_job.status == "processing"
    db.close()
