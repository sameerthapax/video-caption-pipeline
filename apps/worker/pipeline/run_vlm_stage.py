from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path

from core.config import settings
from pipeline.audio_windows import build_transcript_windows, extract_audio_window_files
from pipeline.global_summary import fuse_segment_ground_truth, generate_global_summary
from pipeline.video_memory import create_video_memory, merge_segment_into_memory
from pipeline.vlm_reasoning import analyze_segment, build_failed_segment_response, serialize_segment_error
from pipeline.temporal_segments import assign_transcript_chunks_to_segments
from schemas.segments import TemporalSegment, TemporalSegmentsArtifact
from schemas.transcription import TranscriptionRequestArtifact, TranscriptChunk
from schemas.vlm import GlobalFactualSummary, SegmentVlmResponse, VlmSegmentArtifactEntry, VlmSegmentsArtifact
from services.fireworks_client import FireworksClient, FireworksConfig
from services.google_gemini_client import GoogleGeminiClient, GoogleGeminiConfig, GoogleGeminiError
from services.job_status import update_job_status
from services.supabase_storage import StorageDownloadError, StorageUploadError, download_to_path, upload_file_async

logger = logging.getLogger("video-caption-pipeline.worker")

PROGRESS_STEPS = {
    "loading_temporal_segments": 10,
    "processing_segment_1": 20,
    "processing_segment_2": 35,
    "processing_segment_3": 50,
    "processing_segment_4": 65,
    "processing_segment_5": 75,
    "generating_global_summary": 85,
    "vlm_reasoning_completed": 90,
}


async def run_vlm_reasoning_stage(
    job_id: str,
    bucket: str,
    temporal_segments_storage_path: str,
    local_temporal_segments_path: str | None = None,
    local_audio_path: str | None = None,
    local_frame_sampling_path: str | None = None,
    transcription_source_audio_storage_path: str = "",
    reuse_local_segment_frames: bool = False,
    keep_local_artifacts: bool = False,
) -> dict:
    if not settings.fireworks_api_key:
        raise ValueError("FIREWORKS_API_KEY is required for the VLM reasoning stage.")
    if not settings.fireworks_model:
        raise ValueError("FIREWORKS_MODEL is required for the VLM reasoning stage.")

    temp_root = (
        Path(local_temporal_segments_path).parent
        if local_temporal_segments_path
        else Path(settings.worker_tmp_root) / f"{job_id}-vlm"
    )
    storage_prefix = f"processed/{job_id}"
    local_segments_path = Path(local_temporal_segments_path) if local_temporal_segments_path else temp_root / "temporal_segments.json"
    fireworks = FireworksClient(
        FireworksConfig(
            api_key=settings.fireworks_api_key,
            base_url=settings.fireworks_base_url,
            timeout_seconds=settings.fireworks_timeout_seconds,
            max_retries=settings.fireworks_max_retries,
        )
    )
    gemini_client = GoogleGeminiClient(
        GoogleGeminiConfig(
            api_key=settings.google_gemini_api_key or "",
            base_url=settings.google_gemini_base_url,
            model=settings.google_gemini_transcription_model,
            timeout_seconds=settings.google_gemini_timeout_seconds,
        )
    )

    _set_job_step(job_id=job_id, current_step="vlm_reasoning_started", progress=0)
    _set_job_step(job_id=job_id, current_step="loading_temporal_segments", progress=PROGRESS_STEPS["loading_temporal_segments"])

    try:
        temp_root.mkdir(parents=True, exist_ok=True)
        if local_temporal_segments_path:
            logger.info("Using local temporal segments for job %s at %s", job_id, local_segments_path)
        else:
            download_to_path(bucket=bucket, object_path=temporal_segments_storage_path, destination=local_segments_path)
        temporal_segments = TemporalSegmentsArtifact.model_validate_json(local_segments_path.read_text(encoding="utf-8"))
        frame_upload_task = asyncio.create_task(_upload_segment_frames(bucket=bucket, segments=temporal_segments.segments))
        transcript_task = asyncio.create_task(
            _run_transcript_branch(
                job_id=job_id,
                gemini_client=gemini_client,
                temporal_segments=temporal_segments,
                local_audio_path=local_audio_path,
                source_audio_storage_path=transcription_source_audio_storage_path,
                bucket=bucket,
                storage_prefix=storage_prefix,
                temp_root=temp_root,
            )
        )
        visual_task = asyncio.create_task(
            _run_visual_branch(
                fireworks=fireworks,
                job_id=job_id,
                temporal_segments=temporal_segments,
                bucket=bucket,
                storage_prefix=storage_prefix,
                temp_root=temp_root,
                reuse_local_segment_frames=reuse_local_segment_frames,
            )
        )

        transcription_request, transcript_buckets = await transcript_task
        segment_artifact, video_memory = await visual_task
        await frame_upload_task

        previous_meta: dict = {"last_frame": {}, "last_transcript_chunk": {}, "last_segment_summary": ""}
        for segment in temporal_segments.segments:
            segment.transcript_chunks = transcript_buckets[segment.segment_index]
            visual_entry = next(item for item in segment_artifact.segments if item.segment_index == segment.segment_index)
            ground_truth = await fuse_segment_ground_truth(
                client=fireworks,
                model=settings.fireworks_model or "",
                job_id=job_id,
                segment=segment,
                visual_response=visual_entry.vlm_response.model_dump(),
                previous_segment_meta=previous_meta,
            )
            segment.segment_ground_truth = ground_truth
            previous_meta = {
                "last_frame": (
                    {
                        "frame_id": segment.frames[-1].frame_id,
                        "timestamp": segment.frames[-1].timestamp,
                    }
                    if segment.frames
                    else {}
                ),
                "last_transcript_chunk": (
                    {
                        "start": segment.transcript_chunks[-1].start,
                        "end": segment.transcript_chunks[-1].end,
                        "text": segment.transcript_chunks[-1].text,
                    }
                    if segment.transcript_chunks
                    else {}
                ),
                "last_segment_summary": ground_truth.get("scene_summary", ""),
            }

        temporal_segments_path = temp_root / "temporal_segments.json"
        video_memory_path = temp_root / "video_memory.json"
        temporal_segments_path.write_text(temporal_segments.model_dump_json(indent=2), encoding="utf-8")
        video_memory_path.write_text(video_memory.model_dump_json(indent=2), encoding="utf-8")
        temporal_upload_task = asyncio.create_task(
            _upload_post_fusion_artifacts(
                bucket=bucket,
                storage_prefix=storage_prefix,
                temporal_segments_path=temporal_segments_path,
                video_memory_path=video_memory_path,
                local_frame_sampling_path=Path(local_frame_sampling_path) if local_frame_sampling_path else None,
            )
        )

        _set_job_step(job_id=job_id, current_step="generating_global_summary", progress=PROGRESS_STEPS["generating_global_summary"])
        global_summary = await generate_global_summary(
            client=fireworks,
            model=settings.fireworks_model or "",
            job_id=job_id,
            video_memory=video_memory,
            segment_artifact=segment_artifact,
            temporal_segments=temporal_segments,
            all_frame_paths=_collect_all_frame_paths(temporal_segments.segments),
        )
        global_summary_path = temp_root / "global_factual_summary.json"
        global_summary_path.write_text(global_summary.model_dump_json(indent=2), encoding="utf-8")
        global_summary_upload = asyncio.create_task(
            upload_file_async(
                bucket=bucket,
                object_path=f"{storage_prefix}/global_factual_summary.json",
                source=global_summary_path,
                content_type="application/json",
            )
        )

        post_fusion_paths = await temporal_upload_task
        global_summary_upload_path = await global_summary_upload
        artifact_paths = {
            **post_fusion_paths,
            "global_factual_summary_json": global_summary_upload_path,
            "local_temporal_segments_json": str(temporal_segments_path),
            "local_video_memory_json": str(video_memory_path),
            "local_global_factual_summary_json": str(global_summary_path),
        }
        update_job_status(
            job_id=job_id,
            status="processing",
            current_step="vlm_reasoning_completed",
            progress=PROGRESS_STEPS["vlm_reasoning_completed"],
            error_message="",
            artifact_paths=artifact_paths,
        )
        return artifact_paths
    except (StorageDownloadError, StorageUploadError, RuntimeError, ValueError) as exc:
        logger.exception("VLM reasoning stage failed for job %s", job_id)
        update_job_status(
            job_id=job_id,
            status="failed",
            current_step="vlm_reasoning_failed",
            progress=PROGRESS_STEPS["generating_global_summary"],
            error_message=str(exc),
        )
        raise
    finally:
        if settings.debug_keep_temp or keep_local_artifacts or local_temporal_segments_path:
            logger.info("Keeping temp directory for job %s at %s due to DEBUG_KEEP_TEMP=true", job_id, temp_root)
        else:
            shutil.rmtree(temp_root, ignore_errors=True)


async def _run_visual_branch(
    *,
    fireworks: FireworksClient,
    job_id: str,
    temporal_segments: TemporalSegmentsArtifact,
    bucket: str,
    storage_prefix: str,
    temp_root: Path,
    reuse_local_segment_frames: bool,
) -> tuple[VlmSegmentsArtifact, object]:
    memory = create_video_memory(job_id=job_id)
    segment_artifact = VlmSegmentsArtifact(job_id=job_id)
    successful_segments = 0

    for segment in temporal_segments.segments:
        _set_job_step(
            job_id=job_id,
            current_step=f"processing_segment_{segment.segment_index + 1}",
            progress=PROGRESS_STEPS[f"processing_segment_{segment.segment_index + 1}"],
        )
        prepared_segment = _prepare_segment_frames(
            bucket=bucket,
            temp_root=temp_root,
            segment=segment,
            reuse_local_segment_frames=reuse_local_segment_frames,
        )
        response = await _process_segment(
            fireworks=fireworks,
            job_id=job_id,
            segment=prepared_segment,
            memory=memory,
        )
        if response.status != "failed":
            successful_segments += 1
        memory = merge_segment_into_memory(memory=memory, segment=prepared_segment, response=response)
        segment_artifact.segments.append(
            VlmSegmentArtifactEntry(
                segment_index=prepared_segment.segment_index,
                input_frames=prepared_segment.frames,
                input_transcript_chunks=[],
                vlm_response=response,
            )
        )

    if successful_segments == 0:
        raise RuntimeError("All segment VLM calls failed; cannot generate a global factual summary.")

    vlm_segments_path = temp_root / "vlm_segments.json"
    vlm_segments_path.write_text(segment_artifact.model_dump_json(indent=2), encoding="utf-8")
    await upload_file_async(
        bucket=bucket,
        object_path=f"{storage_prefix}/vlm_segments.json",
        source=vlm_segments_path,
        content_type="application/json",
    )
    return segment_artifact, memory


async def _run_transcript_branch(
    *,
    job_id: str,
    gemini_client: GoogleGeminiClient,
    temporal_segments: TemporalSegmentsArtifact,
    local_audio_path: str | None,
    source_audio_storage_path: str,
    bucket: str,
    storage_prefix: str,
    temp_root: Path,
) -> tuple[TranscriptionRequestArtifact, list[list[TranscriptChunk]]]:
    max_concurrency = 4
    transcript_windows = build_transcript_windows(temporal_segments.video_metadata.duration, window_seconds=5.0)
    notes = [
        "Transcript chunks are aligned to 5-second windows.",
        "Transcript generation runs in parallel with visual-only segment analysis.",
        f"Gemini transcription concurrency is capped at {max_concurrency} windows.",
    ]
    transcript_chunks = transcript_windows
    status = "skipped"
    if local_audio_path:
        if not settings.google_gemini_api_key:
            raise ValueError("GOOGLE_GEMINI_API_KEY is required for Gemini transcription.")
        audio_windows_dir = temp_root / "audio_windows"
        extracted_windows = await asyncio.to_thread(
            extract_audio_window_files,
            source_audio_path=Path(local_audio_path),
            output_dir=audio_windows_dir,
            transcript_windows=transcript_windows,
        )
        semaphore = asyncio.Semaphore(max_concurrency)
        transcript_chunks = await asyncio.gather(
            *[
                _transcribe_window_safe(
                    job_id=job_id,
                    gemini_client=gemini_client,
                    semaphore=semaphore,
                    audio_path=window.path,
                    start=window.start,
                    end=window.end,
                )
                for window in extracted_windows
            ]
        )
        status = "completed"
    else:
        notes.append("No clean audio was available, so transcript chunks remain empty.")

    transcription_request = TranscriptionRequestArtifact(
        job_id=job_id,
        source_audio_storage_path=source_audio_storage_path,
        provider="google_gemini",
        status=status,
        provider_metadata=gemini_client.build_transcription_request_metadata(),
        notes=notes,
        transcript_chunks=transcript_chunks,
    )
    transcription_request_path = temp_root / "transcription_request.json"
    transcription_request_path.write_text(transcription_request.model_dump_json(indent=2), encoding="utf-8")
    await upload_file_async(
        bucket=bucket,
        object_path=f"{storage_prefix}/transcription_request.json",
        source=transcription_request_path,
        content_type="application/json",
    )
    buckets = assign_transcript_chunks_to_segments(
        transcript_chunks=transcript_chunks,
        duration=temporal_segments.video_metadata.duration,
        segment_count=len(temporal_segments.segments),
    )
    return transcription_request, buckets


async def _process_segment(
    *,
    fireworks: FireworksClient,
    job_id: str,
    segment: TemporalSegment,
    memory,
) -> SegmentVlmResponse:
    try:
        return await analyze_segment(
            client=fireworks,
            model=settings.fireworks_model or "",
            job_id=job_id,
            segment=segment,
            memory=memory,
            include_transcript=False,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Segment %s failed for job %s", segment.segment_index, job_id)
        error_message = serialize_segment_error(exc)
        return build_failed_segment_response(segment=segment, error_message=error_message)


def _prepare_segment_frames(
    *,
    bucket: str,
    temp_root: Path,
    segment: TemporalSegment,
    reuse_local_segment_frames: bool = False,
) -> TemporalSegment:
    for frame in segment.frames:
        if reuse_local_segment_frames and frame.local_path and Path(frame.local_path).exists():
            continue
        local_frame_path = temp_root / "frames" / Path(frame.storage_path).name
        if not local_frame_path.exists():
            local_frame_path.parent.mkdir(parents=True, exist_ok=True)
            download_to_path(bucket=bucket, object_path=frame.storage_path, destination=local_frame_path)
        frame.local_path = str(local_frame_path)
    return segment


async def _upload_segment_frames(*, bucket: str, segments: list[TemporalSegment]) -> list[str]:
    deduped: dict[str, Path] = {}
    for segment in segments:
        for frame in segment.frames:
            deduped[frame.storage_path] = Path(frame.local_path)
    return await asyncio.gather(
        *[
            upload_file_async(
                bucket=bucket,
                object_path=storage_path,
                source=source,
                content_type="image/jpeg",
            )
            for storage_path, source in deduped.items()
        ]
    )


async def _upload_post_fusion_artifacts(
    *,
    bucket: str,
    storage_prefix: str,
    temporal_segments_path: Path,
    video_memory_path: Path,
    local_frame_sampling_path: Path | None,
) -> dict[str, str]:
    tasks = [
        upload_file_async(
            bucket=bucket,
            object_path=f"{storage_prefix}/temporal_segments.json",
            source=temporal_segments_path,
            content_type="application/json",
        ),
        upload_file_async(
            bucket=bucket,
            object_path=f"{storage_prefix}/video_memory.json",
            source=video_memory_path,
            content_type="application/json",
        ),
    ]
    if local_frame_sampling_path is not None:
        tasks.append(
            upload_file_async(
                bucket=bucket,
                object_path=f"{storage_prefix}/frame_sampling.json",
                source=local_frame_sampling_path,
                content_type="application/json",
            )
        )
    uploads = await asyncio.gather(*tasks)
    result = {
        "temporal_segments_json": uploads[0],
        "video_memory_json": uploads[1],
    }
    if local_frame_sampling_path is not None:
        result["frame_sampling_json"] = uploads[2]
    return result


def _collect_all_frame_paths(segments: list[TemporalSegment]) -> list[str]:
    seen: set[str] = set()
    paths: list[str] = []
    for segment in segments:
        for frame in segment.frames:
            if frame.local_path and frame.local_path not in seen:
                seen.add(frame.local_path)
                paths.append(frame.local_path)
    return paths


async def _transcribe_window_safe(
    *,
    job_id: str,
    gemini_client: GoogleGeminiClient,
    semaphore: asyncio.Semaphore,
    audio_path: Path,
    start: float,
    end: float,
) -> TranscriptChunk:
    async with semaphore:
        try:
            return await gemini_client.transcribe_audio_window(audio_path=audio_path, start=start, end=end)
        except GoogleGeminiError as exc:
            logger.warning("Transcript window failed for job %s at %.2f-%.2fs: %s", job_id, start, end, exc)
            return TranscriptChunk(start=start, end=end, text="", expressive_transcript="")


def _set_job_step(*, job_id: str, current_step: str, progress: int) -> None:
    logger.info("Job %s step=%s progress=%s", job_id, current_step, progress)
    update_job_status(
        job_id=job_id,
        status="processing",
        current_step=current_step,
        progress=progress,
        error_message="",
    )
