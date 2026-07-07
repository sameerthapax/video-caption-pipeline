from __future__ import annotations

from pipeline.describe_frames import describe_frames
from pipeline.extract_frames import extract_frames
from pipeline.normalize import normalize_video
from pipeline.style import style_captions
from pipeline.summarize import summarize_content
from pipeline.transcribe import transcribe_audio
from services.jobs import claim_next_job


def run_worker_iteration() -> None:
    job = claim_next_job()
    if job is None:
        return

    job_id = job["id"]
    normalize_video(job_id)
    extract_frames(job_id)
    transcribe_audio(job_id)
    describe_frames(job_id)
    summarize_content(job_id)
    style_captions(job_id)
