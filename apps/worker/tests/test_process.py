from pathlib import Path

import pytest

from services.process import ProbeMetadata, parse_ffprobe_output
from services.processor import JobProcessingError, _build_cleaned_object_path, _validate_media


def test_parse_ffprobe_output_handles_expected_payload():
    metadata = parse_ffprobe_output(
        """
        {
          "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "12.5", "size": "2048"},
          "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "avg_frame_rate": "30000/1001"},
            {"codec_type": "audio", "codec_name": "aac"}
          ]
        }
        """
    )

    assert metadata.format_name.startswith("mov")
    assert metadata.duration_seconds == 12.5
    assert metadata.file_size_bytes == 2048
    assert metadata.video_codec == "h264"
    assert metadata.audio_codec == "aac"
    assert metadata.has_audio is True
    assert metadata.fps == pytest.approx(29.97002997)


def test_validate_media_rejects_empty_file(tmp_path, monkeypatch):
    from core.database import SessionLocal
    from models.job import VideoJob

    source_path = tmp_path / "clip.mp4"
    source_path.write_bytes(b"")

    db = SessionLocal()
    job = VideoJob(
        id="job-2",
        user_id="user-2",
        original_filename="clip.mp4",
        storage_bucket="videos",
        video_path="user-2/job-2/clip.mp4",
        upload_content_type="video/mp4",
        upload_file_size=0,
        status="processing",
        current_step="downloaded",
        progress=25,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    with pytest.raises(JobProcessingError, match="empty"):
        _validate_media(db=db, job=job, input_path=source_path)

    assert job.current_step == "validation_failed"
    db.close()


def test_build_cleaned_object_path_uses_same_job_folder():
    from models.job import VideoJob

    job = VideoJob(
        id="job-3",
        user_id="user-3",
        original_filename="clip.mov",
        storage_bucket="videos",
        video_path="user-3/job-3/clip.mov",
        upload_content_type="video/quicktime",
        upload_file_size=10,
        status="processing",
        current_step="preprocessing",
        progress=55,
    )

    assert _build_cleaned_object_path(job=job, suffix="video", extension=".mp4") == "user-3/job-3/cleaned_clip_video.mp4"
    assert _build_cleaned_object_path(job=job, suffix="audio", extension=".wav") == "user-3/job-3/cleaned_clip_audio.wav"
