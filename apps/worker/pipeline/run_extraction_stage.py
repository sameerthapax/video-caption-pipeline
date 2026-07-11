from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from core.config import settings
from pipeline.extract_frames import extract_selected_frames
from pipeline.frame_sampling import build_frame_sampling_artifact
from pipeline.probe_video import probe_video_metadata
from pipeline.scene_change import analyze_scene_changes
from pipeline.temporal_segments import build_temporal_segments_artifact
from schemas.segments import SamplingConfig
from services.job_status import update_job_status
from services.process import ProcessExecutionError
from services.supabase_storage import (
    StorageDownloadError,
    StorageUploadError,
    download_to_path,
    try_download_to_path,
    upload_file_async,
)

logger = logging.getLogger("video-caption-pipeline.worker")

PROGRESS_STEPS = {
    "downloading_clean_assets": 10,
    "probing_video": 20,
    "creating_transcript_windows": 30,
    "sampling_frames": 45,
    "extracting_frames": 60,
    "building_temporal_segments": 75,
    "uploading_artifacts": 90,
    "extraction_completed": 100,
}


async def run_video_extraction_stage(
    job_id: str,
    bucket: str,
    clean_video_storage_path: str,
    clean_audio_storage_path: str,
    finalize_job: bool = True,
    local_video_path_override: str | None = None,
    local_audio_path_override: str | None = None,
    keep_local_artifacts: bool = False,
    upload_artifacts: bool = True,
) -> dict:
    temp_root = Path("/tmp") / job_id
    frames_dir = temp_root / "frames"
    local_video_path = Path(local_video_path_override) if local_video_path_override else temp_root / Path(clean_video_storage_path).name
    local_audio_path = (
        Path(local_audio_path_override)
        if local_audio_path_override
        else temp_root / Path(clean_audio_storage_path).name
        if clean_audio_storage_path
        else temp_root / "audio.wav"
    )
    storage_prefix = f"processed/{job_id}"
    sampling_config = SamplingConfig()

    _set_job_step(job_id=job_id, current_step="downloading_clean_assets", progress=PROGRESS_STEPS["downloading_clean_assets"])
    try:
        temp_root.mkdir(parents=True, exist_ok=True)
        if local_video_path_override:
            logger.info("Using local cleaned video for job %s at %s", job_id, local_video_path)
        else:
            download_to_path(bucket=bucket, object_path=clean_video_storage_path, destination=local_video_path)
        downloaded_audio_path: Path | None = None
        if local_audio_path_override:
            downloaded_audio_path = local_audio_path
            logger.info("Using local cleaned audio for job %s at %s", job_id, local_audio_path)
        elif clean_audio_storage_path:
            downloaded_audio_path = try_download_to_path(
                bucket=bucket,
                object_path=clean_audio_storage_path,
                destination=local_audio_path,
            )

        _set_job_step(job_id=job_id, current_step="probing_video", progress=PROGRESS_STEPS["probing_video"])
        video_metadata = probe_video_metadata(local_video_path)

        _set_job_step(job_id=job_id, current_step="sampling_frames", progress=PROGRESS_STEPS["sampling_frames"])
        frame_sampling = await _build_frame_sampling_async(
            job_id=job_id,
            local_video_path=local_video_path,
            video_metadata=video_metadata,
            sampling_config=sampling_config,
        )

        _set_job_step(job_id=job_id, current_step="extracting_frames", progress=PROGRESS_STEPS["extracting_frames"])
        frames = await asyncio.to_thread(
            extract_selected_frames,
            job_id=job_id,
            video_path=local_video_path,
            output_dir=frames_dir,
            storage_prefix=f"{storage_prefix}/frames",
            timestamps_with_reasons=[
                (item.timestamp, item.selection_reasons, item.scene_change_score)
                for item in frame_sampling.final_selected_frames
            ],
            max_width=settings.frame_extract_width,
        )

        _set_job_step(
            job_id=job_id,
            current_step="building_temporal_segments",
            progress=PROGRESS_STEPS["building_temporal_segments"],
        )
        temporal_segments = build_temporal_segments_artifact(
            job_id=job_id,
            video_metadata=video_metadata,
            sampling_config=sampling_config,
            frames=frames,
            transcript_chunks=[],
        )

        frame_sampling_path = temp_root / "frame_sampling.json"
        temporal_segments_path = temp_root / "temporal_segments.json"
        frame_sampling_path.write_text(frame_sampling.model_dump_json(indent=2), encoding="utf-8")
        temporal_segments_path.write_text(temporal_segments.model_dump_json(indent=2), encoding="utf-8")

        artifact_paths = {
            "frames": [frame.storage_path for frame in frames],
            "frame_sampling_json": f"{storage_prefix}/frame_sampling.json",
            "temporal_segments_json": f"{storage_prefix}/temporal_segments.json",
            "local_temporal_segments_json": str(temporal_segments_path),
            "local_frame_sampling_json": str(frame_sampling_path),
            "local_video_path": str(local_video_path),
            "local_audio_path": str(downloaded_audio_path) if downloaded_audio_path else "",
        }

        if upload_artifacts:
            _set_job_step(job_id=job_id, current_step="uploading_artifacts", progress=PROGRESS_STEPS["uploading_artifacts"])
            uploaded_frame_paths = await asyncio.gather(
                *[
                    upload_file_async(
                        bucket=bucket,
                        object_path=frame.storage_path,
                        source=Path(frame.local_path),
                        content_type="image/jpeg",
                    )
                    for frame in frames
                ]
            )
            frame_sampling_upload, temporal_segments_upload = await asyncio.gather(
                upload_file_async(
                    bucket=bucket,
                    object_path=f"{storage_prefix}/frame_sampling.json",
                    source=frame_sampling_path,
                    content_type="application/json",
                ),
                upload_file_async(
                    bucket=bucket,
                    object_path=f"{storage_prefix}/temporal_segments.json",
                    source=temporal_segments_path,
                    content_type="application/json",
                ),
            )
            artifact_paths.update(
                {
                    "frames": uploaded_frame_paths,
                    "frame_sampling_json": frame_sampling_upload,
                    "temporal_segments_json": temporal_segments_upload,
                }
            )

        artifact_paths.update(
            {
                "video_duration_seconds": video_metadata.duration,
                "source_audio_storage_path": clean_audio_storage_path,
            }
        )

        update_job_status(
            job_id=job_id,
            status="completed" if finalize_job else "processing",
            current_step="extraction_completed",
            progress=PROGRESS_STEPS["extraction_completed"],
            error_message="",
            artifact_paths=artifact_paths,
        )
        return artifact_paths
    except (ProcessExecutionError, StorageDownloadError, StorageUploadError, RuntimeError, ValueError) as exc:
        logger.exception("Extraction stage failed for job %s", job_id)
        update_job_status(
            job_id=job_id,
            status="failed",
            current_step="extraction_failed",
            progress=PROGRESS_STEPS.get("uploading_artifacts", 90),
            error_message=str(exc),
        )
        raise
    finally:
        if settings.debug_keep_temp or keep_local_artifacts:
            logger.info("Keeping temp directory for job %s at %s due to DEBUG_KEEP_TEMP=true", job_id, temp_root)
        else:
            shutil.rmtree(temp_root, ignore_errors=True)


def _set_job_step(*, job_id: str, current_step: str, progress: int) -> None:
    logger.info("Job %s step=%s progress=%s", job_id, current_step, progress)
    update_job_status(
        job_id=job_id,
        status="processing",
        current_step=current_step,
        progress=progress,
        error_message="",
    )


async def _build_frame_sampling_async(
    *,
    job_id: str,
    local_video_path: Path,
    video_metadata,
    sampling_config: SamplingConfig,
):
    logger.info("Starting frame sampling branch for job %s in parallel with transcription", job_id)
    scene_change_result = await asyncio.to_thread(
        analyze_scene_changes,
        video_path=local_video_path,
        duration=video_metadata.duration,
    )
    return await asyncio.to_thread(
        build_frame_sampling_artifact,
        job_id=job_id,
        video_metadata=video_metadata,
        scene_change_result=scene_change_result,
        sampling_config=sampling_config,
    )
