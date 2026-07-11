from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import shutil
from collections.abc import Generator, Iterator
from pathlib import Path

from sqlalchemy.orm import Session

from core.config import settings
from models.job import VideoJob
from pipeline.style import style_captions
from pipeline.run_extraction_stage import run_video_extraction_stage
from pipeline.run_vlm_stage import run_vlm_reasoning_stage
from services.events import WorkerProgressEvent
from services.fireworks_client import FireworksClient, FireworksConfig
from services.jobs import claim_job_for_processing, update_job_progress
from services.openai_responses_client import OpenAIResponsesClient, OpenAIResponsesConfig
from services.process import ProcessExecutionError, ProbeMetadata, probe_media, run_command
from services.results import upsert_caption_result
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

        cleaned_artifacts = yield from _preprocess_media(
            db=db,
            job=job,
            input_path=original_input_path,
            processed_dir=processed_dir,
            source_probe=probe_metadata,
        )

        yield WorkerProgressEvent(
            event="extraction_started",
            job_id=job.id,
            step="downloading_clean_assets",
            message="Handing off cleaned assets into the extraction stage.",
            progress=10,
            metadata=cleaned_artifacts,
        )
        artifact_paths = asyncio.run(
            run_video_extraction_stage(
                job_id=job.id,
                bucket=job.storage_bucket,
                clean_video_storage_path=cleaned_artifacts["video_object_path"],
                clean_audio_storage_path=cleaned_artifacts["audio_object_path"] or "",
                finalize_job=False,
                local_video_path_override=cleaned_artifacts["local_video_path"],
                local_audio_path_override=cleaned_artifacts["local_audio_path"],
                keep_local_artifacts=True,
                upload_artifacts=False,
            )
        )
        yield WorkerProgressEvent(
            event="extraction_completed",
            job_id=job.id,
            step="extraction_completed",
            message="Video extraction stage completed.",
            progress=100,
            metadata=artifact_paths,
        )
        yield WorkerProgressEvent(
            event="vlm_reasoning_started",
            job_id=job.id,
            step="loading_temporal_segments",
            message="Starting hierarchical VLM reasoning stage.",
            progress=10,
            metadata={"temporal_segments_json": artifact_paths.get("temporal_segments_json")},
        )
        vlm_artifact_paths = asyncio.run(
            run_vlm_reasoning_stage(
                job_id=job.id,
                bucket=job.storage_bucket,
                temporal_segments_storage_path=artifact_paths["temporal_segments_json"],
                local_temporal_segments_path=artifact_paths.get("local_temporal_segments_json"),
                local_audio_path=artifact_paths.get("local_audio_path"),
                local_frame_sampling_path=artifact_paths.get("local_frame_sampling_json"),
                transcription_source_audio_storage_path=artifact_paths.get("source_audio_storage_path", ""),
                reuse_local_segment_frames=True,
                keep_local_artifacts=True,
            )
        )
        yield WorkerProgressEvent(
            event="vlm_reasoning_completed",
            job_id=job.id,
            step="vlm_reasoning_completed",
            message="Hierarchical VLM reasoning stage completed.",
            progress=90,
            metadata=vlm_artifact_paths,
        )
        yield WorkerProgressEvent(
            event="generating_styled_captions_started",
            job_id=job.id,
            step="generating_styled_captions",
            message="Generating final caption variants from the global factual summary.",
            progress=92,
            metadata={"global_factual_summary_json": vlm_artifact_paths.get("global_factual_summary_json")},
        )
        update_job_progress(db=db, job=job, current_step="generating_styled_captions", progress=92)
        final_result, local_final_result_path, uploaded_final_result_path = asyncio.run(
            _run_final_caption_stage(
                job=job,
                global_summary_path=vlm_artifact_paths["local_global_factual_summary_json"],
                global_summary_storage_path=vlm_artifact_paths["global_factual_summary_json"],
            )
        )
        upsert_caption_result(db=db, job=job, final_result=final_result)
        update_job_progress(
            db=db,
            job=job,
            status="completed",
            current_step="completed",
            progress=100,
            preprocessing_metadata=None,
        )
        job.artifact_paths = {
            **dict(job.artifact_paths or {}),
            "final_result_json": uploaded_final_result_path,
            "local_final_result_json": local_final_result_path,
        }
        db.add(job)
        db.commit()
        db.refresh(job)
        yield WorkerProgressEvent(
            event="completed",
            job_id=job.id,
            step="completed",
            message="Final caption set generated and stored.",
            progress=100,
            metadata={"final_result_json": uploaded_final_result_path},
        )
    except (JobProcessingError, StorageDownloadError, StorageUploadError, ProcessExecutionError, RuntimeError, ValueError) as exc:
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
) -> Generator[WorkerProgressEvent, None, dict[str, str | None]]:
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

    uploaded_audio_object_path: str | None = None
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                upload_private_object,
                bucket=job.storage_bucket,
                object_path=cleaned_video_object_path,
                source=normalized_path,
                content_type="video/mp4",
            )
        ]
        if source_probe.has_audio:
            futures.append(
                executor.submit(
                    upload_private_object,
                    bucket=job.storage_bucket,
                    object_path=cleaned_audio_object_path,
                    source=audio_path,
                    content_type="application/octet-stream",
                )
            )
        for future in futures:
            future.result()

    logger.info("Uploaded cleaned video artifact for job %s to %s", job.id, cleaned_video_object_path)
    if source_probe.has_audio:
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
    return {
        "bucket": job.storage_bucket,
        "video_object_path": cleaned_video_object_path,
        "audio_object_path": uploaded_audio_object_path,
        "local_video_path": str(normalized_path),
        "local_audio_path": str(audio_path) if source_probe.has_audio else None,
    }


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


async def _run_final_caption_stage(
    *,
    job: VideoJob,
    global_summary_path: str,
    global_summary_storage_path: str,
):
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for final caption generation.")
    if not settings.openai_final_caption_model:
        raise ValueError("OPENAI_FINAL_CAPTION_MODEL is required for final caption generation.")

    openai_client = OpenAIResponsesClient(
        OpenAIResponsesConfig(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout_seconds=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
            reasoning_effort=settings.openai_reasoning_effort,
            text_verbosity=settings.openai_text_verbosity,
        )
    )
    storage_prefix = f"processed/{job.id}"
    return await style_captions(
        client=openai_client,
        model=settings.openai_final_caption_model,
        job_id=job.id,
        bucket=job.storage_bucket,
        storage_prefix=storage_prefix,
        global_summary_path=Path(global_summary_path),
        global_summary_storage_path=global_summary_storage_path,
    )
