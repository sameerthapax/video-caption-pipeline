from __future__ import annotations

import logging
import shutil
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy.orm import Session

from core.config import settings
from models.job import VideoJob
from services.events import WorkerProgressEvent
from services.jobs import claim_job_for_processing, update_job_progress
from services.process import ProcessExecutionError, ProbeMetadata, probe_media, run_command
from storage.supabase import StorageDownloadError, StorageUploadError, download_private_object, upload_private_object

logger = logging.getLogger("video-caption-pipeline.worker")

SUPPORTED_VIDEO_CODECS = {"h264", "hevc", "vp9", "av1"}
SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}


class JobProcessingError(RuntimeError):
    pass


def process_video_job(*, db: Session, job_id: str) -> Iterator[WorkerProgressEvent]:
    logger.info("Worker received job %s", job_id)
    job, claimed = claim_job_for_processing(db=db, job_id=job_id)
    if job is None:
        yield WorkerProgressEvent(
            event="worker_skipped",
            job_id=job_id,
            step="claim_skipped",
            message="Job was not available for claiming.",
            progress=5,
        )
        return
    if not claimed:
        yield WorkerProgressEvent(
            event="worker_skipped",
            job_id=job_id,
            step=job.current_step,
            message=f"Job is already in status {job.status}.",
            progress=job.progress,
            metadata={"status": job.status},
        )
        return

    logger.info("Worker claimed job %s", job_id)
    yield WorkerProgressEvent(
        event="claimed",
        job_id=job.id,
        step="claimed",
        message=f"Worker claimed job {job.id}.",
        progress=5,
    )

    temp_root = Path(settings.worker_tmp_root) / job.id
    input_dir = temp_root / "input"
    processed_dir = temp_root / "processed"
    artifacts_dir = temp_root / "artifacts"
    original_input_path = input_dir / f"original{_resolve_extension(job)}"

    try:
        input_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Created working directories for job %s at %s", job.id, temp_root)

        yield from _download_job_media(db=db, job=job, destination=original_input_path)

        update_job_progress(db=db, job=job, current_step="validating", progress=30)
        yield WorkerProgressEvent(
            event="validating_started",
            job_id=job.id,
            step="validating",
            message="Validating downloaded video.",
            progress=30,
        )
        probe_metadata = _validate_media(db=db, job=job, input_path=original_input_path)
        yield WorkerProgressEvent(
            event="validating_completed",
            job_id=job.id,
            step="validated",
            message="Video validation completed.",
            progress=45,
            metadata=_metadata_dict(probe_metadata),
        )

        yield from _preprocess_media(
            db=db,
            job=job,
            input_path=original_input_path,
            processed_dir=processed_dir,
            source_probe=probe_metadata,
        )

        update_job_progress(
            db=db,
            job=job,
            status="processing",
            current_step="preprocessing_completed",
            progress=95,
            error_message="",
        )
        logger.info("Worker left job %s in preprocessing_completed for downstream stages", job.id)
    except (JobProcessingError, StorageDownloadError, StorageUploadError, ProcessExecutionError) as exc:
        safe_message = str(exc)
        logger.exception("Worker failed job %s during step %s: %s", job.id, job.current_step, safe_message)
        update_job_progress(
            db=db,
            job=job,
            status="failed",
            current_step=job.current_step or "failed",
            progress=job.progress,
            error_message=safe_message,
        )
        yield WorkerProgressEvent(
            event="failed",
            job_id=job.id,
            step=job.current_step or "failed",
            message=safe_message,
            progress=job.progress,
        )
    finally:
        logger.info("Cleaning temp directory for job %s", job_id)
        shutil.rmtree(temp_root, ignore_errors=True)
        logger.info("Cleaned temp directory for job %s", job_id)


def _download_job_media(*, db: Session, job: VideoJob, destination: Path) -> Iterator[WorkerProgressEvent]:
    update_job_progress(db=db, job=job, current_step="downloading", progress=10)
    logger.info(
        "Downloading Supabase object for job %s from bucket=%s path=%s to %s",
        job.id,
        job.storage_bucket,
        job.video_path,
        destination,
    )
    yield WorkerProgressEvent(
        event="downloading_started",
        job_id=job.id,
        step="downloading",
        message="Downloading source video.",
        progress=10,
    )
    download_private_object(bucket=job.storage_bucket, object_path=job.video_path, destination=destination)
    update_job_progress(db=db, job=job, current_step="downloaded", progress=25)
    logger.info("Downloaded source video for job %s (%s bytes)", job.id, destination.stat().st_size)
    yield WorkerProgressEvent(
        event="downloading_completed",
        job_id=job.id,
        step="downloaded",
        message="Downloaded source video.",
        progress=25,
        metadata={"path": str(destination)},
    )


def _validate_media(*, db: Session, job: VideoJob, input_path: Path) -> ProbeMetadata:
    logger.info("Validating downloaded media for job %s at %s", job.id, input_path)
    if not input_path.exists():
        job.current_step = "validation_failed"
        raise JobProcessingError("Downloaded video file is missing.")
    if input_path.stat().st_size <= 0:
        job.current_step = "validation_failed"
        raise JobProcessingError("Downloaded video file is empty.")
    if input_path.stat().st_size > settings.max_video_size_mb * 1024 * 1024:
        job.current_step = "validation_failed"
        raise JobProcessingError("Video file exceeds the configured size limit.")
    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        job.current_step = "validation_failed"
        raise JobProcessingError("Unsupported video container.")

    probe_metadata = probe_media(input_path)
    if not _is_supported_container(probe_metadata.format_name):
        job.current_step = "validation_failed"
        raise JobProcessingError("Unsupported video container.")
    if probe_metadata.duration_seconds <= 0:
        job.current_step = "validation_failed"
        raise JobProcessingError("Video duration could not be determined.")
    if probe_metadata.duration_seconds > settings.max_video_duration_seconds:
        job.current_step = "validation_failed"
        raise JobProcessingError("Video exceeds the configured duration limit.")
    if not probe_metadata.video_codec:
        job.current_step = "validation_failed"
        raise JobProcessingError("Video stream is missing.")
    if probe_metadata.video_codec not in SUPPORTED_VIDEO_CODECS:
        job.current_step = "validation_failed"
        raise JobProcessingError("Unsupported video codec.")

    logger.info(
        "Validated job %s: container=%s codec=%s duration=%.2fs fps=%s resolution=%sx%s has_audio=%s",
        job.id,
        probe_metadata.format_name,
        probe_metadata.video_codec,
        probe_metadata.duration_seconds,
        f"{probe_metadata.fps:.3f}" if probe_metadata.fps is not None else "unknown",
        probe_metadata.width,
        probe_metadata.height,
        probe_metadata.has_audio,
    )
    update_job_progress(
        db=db,
        job=job,
        current_step="validated",
        progress=45,
        preprocessing_metadata=_metadata_dict(probe_metadata),
    )
    return probe_metadata


def _preprocess_media(
    *,
    db: Session,
    job: VideoJob,
    input_path: Path,
    processed_dir: Path,
    source_probe: ProbeMetadata,
) -> Iterator[WorkerProgressEvent]:
    update_job_progress(db=db, job=job, current_step="preprocessing", progress=55)
    logger.info(
        "Starting preprocessing for job %s with source fps=%s and has_audio=%s",
        job.id,
        f"{source_probe.fps:.3f}" if source_probe.fps is not None else "unknown",
        source_probe.has_audio,
    )
    yield WorkerProgressEvent(
        event="preprocessing_started",
        job_id=job.id,
        step="preprocessing",
        message="Preprocessing video and audio.",
        progress=55,
    )

    normalized_path = processed_dir / "normalized.mp4"
    audio_path = processed_dir / "audio.wav"
    cleaned_video_object_path = _build_cleaned_object_path(job=job, suffix="video", extension=".mp4")
    cleaned_audio_object_path = _build_cleaned_object_path(job=job, suffix="audio", extension=".wav")

    ffmpeg_args = [
        settings.ffmpeg_path,
        "-y",
        "-i",
        str(input_path),
        "-c:v",
        "libx264",
        "-r",
        "30",
        "-preset",
        "medium",
        "-movflags",
        "+faststart",
        "-an",
    ]
    ffmpeg_args.append(str(normalized_path))
    run_command(args=ffmpeg_args, timeout_seconds=settings.ffmpeg_timeout_seconds)
    normalized_probe = probe_media(normalized_path)
    logger.info(
        "Normalized video for job %s to %s with codec=%s fps=%s resolution=%sx%s has_audio=%s",
        job.id,
        normalized_path,
        normalized_probe.video_codec,
        f"{normalized_probe.fps:.3f}" if normalized_probe.fps is not None else "unknown",
        normalized_probe.width,
        normalized_probe.height,
        normalized_probe.has_audio,
    )
    update_job_progress(
        db=db,
        job=job,
        current_step="normalized_video_created",
        progress=70,
        preprocessing_metadata={
            "normalized": _metadata_dict(normalized_probe),
            "targets": {"video_fps": 30, "video_has_audio": False},
        },
    )
    yield WorkerProgressEvent(
        event="normalized_video_created",
        job_id=job.id,
        step="normalized_video_created",
        message="Normalized video created at 30 fps with audio detached.",
        progress=70,
        metadata={
            **_metadata_dict(normalized_probe),
            "source_fps": source_probe.fps,
            "target_fps": 30,
            "target_has_audio": False,
        },
    )

    if source_probe.has_audio:
        run_command(
            args=[
                settings.ffmpeg_path,
                "-y",
                "-i",
                str(input_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "24000",
                "-c:a",
                "pcm_s16le",
                str(audio_path),
            ],
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )
        logger.info(
            "Extracted normalized audio for job %s to %s as mono 24kHz PCM WAV",
            job.id,
            audio_path,
        )
        update_job_progress(
            db=db,
            job=job,
            current_step="audio_extracted",
            progress=85,
            preprocessing_metadata={
                "has_audio": True,
                "audio": {
                    "sample_rate_hz": 24000,
                    "channels": 1,
                    "codec": "pcm_s16le",
                    "mime_type": "application/octet-stream",
                    "path": str(audio_path),
                },
            },
        )
        yield WorkerProgressEvent(
            event="audio_extracted",
            job_id=job.id,
            step="audio_extracted",
            message="Extracted mono 24kHz WAV audio.",
            progress=85,
            metadata={
                "sample_rate_hz": 24000,
                "channels": 1,
                "codec": "pcm_s16le",
                "mime_type": "application/octet-stream",
            },
        )
    else:
        logger.info("Job %s has no audio stream; skipping WAV extraction", job.id)
        update_job_progress(
            db=db,
            job=job,
            current_step="audio_missing",
            progress=85,
            preprocessing_metadata={"has_audio": False},
        )
        yield WorkerProgressEvent(
            event="audio_missing",
            job_id=job.id,
            step="audio_missing",
            message="Video has no audio stream; continuing without extracted audio.",
            progress=85,
        )

    update_job_progress(db=db, job=job, current_step="uploading_cleaned_artifacts", progress=90)
    logger.info(
        "Uploading cleaned artifacts for job %s to bucket=%s video=%s audio=%s",
        job.id,
        job.storage_bucket,
        cleaned_video_object_path,
        cleaned_audio_object_path if source_probe.has_audio else None,
    )
    yield WorkerProgressEvent(
        event="uploading_cleaned_artifacts_started",
        job_id=job.id,
        step="uploading_cleaned_artifacts",
        message="Uploading cleaned video and audio artifacts.",
        progress=90,
        metadata={
            "cleaned_video_object_path": cleaned_video_object_path,
            "cleaned_audio_object_path": cleaned_audio_object_path if source_probe.has_audio else None,
        },
    )

    upload_private_object(
        bucket=job.storage_bucket,
        object_path=cleaned_video_object_path,
        source=normalized_path,
        content_type="video/mp4",
    )
    logger.info("Uploaded cleaned video artifact for job %s to %s", job.id, cleaned_video_object_path)

    uploaded_audio_object_path: str | None = None
    if source_probe.has_audio:
        upload_private_object(
            bucket=job.storage_bucket,
            object_path=cleaned_audio_object_path,
            source=audio_path,
            content_type="application/octet-stream",
        )
        uploaded_audio_object_path = cleaned_audio_object_path
        logger.info("Uploaded cleaned audio artifact for job %s to %s", job.id, cleaned_audio_object_path)

    update_job_progress(
        db=db,
        job=job,
        current_step="preprocessing_completed",
        progress=95,
        preprocessing_metadata={
            "normalized": _metadata_dict(normalized_probe),
            "has_audio": source_probe.has_audio,
            "targets": {"video_fps": 30, "video_has_audio": False, "audio_sample_rate_hz": 24000},
            "cleaned_artifacts": {
                "video_object_path": cleaned_video_object_path,
                "audio_object_path": uploaded_audio_object_path,
                "bucket": job.storage_bucket,
            },
        },
    )
    logger.info(
        "Preprocessing completed for job %s. Uploaded cleaned_video=%s cleaned_audio=%s",
        job.id,
        cleaned_video_object_path,
        uploaded_audio_object_path,
    )
    yield WorkerProgressEvent(
        event="preprocessing_completed",
        job_id=job.id,
        step="preprocessing_completed",
        message="Preprocessing completed.",
        progress=95,
        metadata={
            "cleaned_artifacts": {
                "bucket": job.storage_bucket,
                "video_object_path": cleaned_video_object_path,
                "audio_object_path": uploaded_audio_object_path,
            },
            "normalized_video": {"fps": normalized_probe.fps, "codec": normalized_probe.video_codec},
            "audio": {"sample_rate_hz": 24000 if source_probe.has_audio else None},
        },
    )


def _resolve_extension(job: VideoJob) -> str:
    suffix = Path(job.original_filename).suffix.lower()
    if suffix in SUPPORTED_EXTENSIONS:
        return suffix
    video_path_suffix = Path(job.video_path).suffix.lower()
    if video_path_suffix in SUPPORTED_EXTENSIONS:
        return video_path_suffix
    return ".bin"


def _metadata_dict(probe_metadata: ProbeMetadata) -> dict[str, object]:
    return {
        "duration_seconds": probe_metadata.duration_seconds,
        "width": probe_metadata.width,
        "height": probe_metadata.height,
        "fps": probe_metadata.fps,
        "video_codec": probe_metadata.video_codec,
        "audio_codec": probe_metadata.audio_codec,
        "file_size_bytes": probe_metadata.file_size_bytes,
        "format_name": probe_metadata.format_name,
        "has_audio": probe_metadata.has_audio,
    }


def _is_supported_container(format_name: str) -> bool:
    format_tokens = {token.strip() for token in format_name.split(",") if token.strip()}
    return bool(format_tokens & {"mp4", "mov", "matroska", "webm"})


def _build_cleaned_object_path(*, job: VideoJob, suffix: str, extension: str) -> str:
    parent_prefix = str(Path(job.video_path).parent)
    stem = Path(job.original_filename).stem
    filename = f"cleaned_{stem}_{suffix}{extension}"
    return f"{parent_prefix}/{filename}"
