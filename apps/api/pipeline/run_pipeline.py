from typing import Any

from django.db import close_old_connections

from video_jobs.models import VideoCaptionResult, VideoJob
from .describe_frames import describe_frames
from .extract_frames import extract_frames
from .neutral_summary import generate_neutral_summary
from .normalize_video import normalize_video
from .styled_captions import generate_styled_captions
from .transcribe_audio import transcribe_audio


PIPELINE_STEPS = [
    ("normalizing_video", 15),
    ("extracting_frames", 30),
    ("transcribing_audio", 45),
    ("describing_frames", 60),
    ("generating_neutral_summary", 78),
    ("generating_styled_captions", 92),
    ("completed", 100),
]


def update_job(job: VideoJob, *, status: str, step: str, progress: int, error_message: str = "") -> None:
    job.status = status
    job.current_step = step
    job.progress = progress
    job.error_message = error_message
    job.save(update_fields=["status", "current_step", "progress", "error_message", "updated_at"])


def run_video_pipeline(job_id: str) -> None:
    close_old_connections()
    job = VideoJob.objects.get(pk=job_id)

    try:
        update_job(job, status=VideoJob.Status.PROCESSING, step="normalizing_video", progress=15)
        normalized = normalize_video(job.video_path)

        update_job(job, status=VideoJob.Status.PROCESSING, step="extracting_frames", progress=30)
        frames = extract_frames(normalized["normalized_video_path"])

        update_job(job, status=VideoJob.Status.PROCESSING, step="transcribing_audio", progress=45)
        transcript = transcribe_audio(normalized["normalized_video_path"])

        update_job(job, status=VideoJob.Status.PROCESSING, step="describing_frames", progress=60)
        frame_descriptions = describe_frames(normalized["normalized_video_path"])

        update_job(job, status=VideoJob.Status.PROCESSING, step="generating_neutral_summary", progress=78)
        summary = generate_neutral_summary(
            transcript["transcript"],
            frame_descriptions["descriptions"],
        )

        update_job(job, status=VideoJob.Status.PROCESSING, step="generating_styled_captions", progress=92)
        styled = generate_styled_captions(summary)

        raw_pipeline_json: dict[str, Any] = {
            "normalized": normalized,
            "frames": frames,
            "transcript": transcript,
            "frame_descriptions": frame_descriptions,
        }

        VideoCaptionResult.objects.update_or_create(
            job=job,
            defaults={
                "neutral_summary": summary,
                "formal_caption": styled["formal_caption"],
                "sarcastic_caption": styled["sarcastic_caption"],
                "humorous_tech_caption": styled["humorous_tech_caption"],
                "humorous_non_tech_caption": styled["humorous_non_tech_caption"],
                "raw_pipeline_json": raw_pipeline_json,
            },
        )

        update_job(job, status=VideoJob.Status.COMPLETED, step="completed", progress=100)
    except Exception as exc:  # pragma: no cover - defensive path for background execution
        update_job(
            job,
            status=VideoJob.Status.FAILED,
            step="failed",
            progress=100,
            error_message=str(exc),
        )
    finally:
        close_old_connections()
