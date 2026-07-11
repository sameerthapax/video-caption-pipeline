from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import boto3

from core.config import settings
from pipeline.run_extraction_stage import run_video_extraction_stage
from pipeline.run_vlm_stage import run_vlm_reasoning_stage
from pipeline.style import style_captions
from services.openai_responses_client import OpenAIResponsesClient, OpenAIResponsesConfig
from services.process import ProcessExecutionError, probe_media, run_command
//
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
secretsmanager = boto3.client("secretsmanager")

JOBS_TABLE = os.environ["JOBS_TABLE"]
ARTIFACT_BUCKET = os.environ["ARTIFACT_BUCKET"]
MODEL_SECRET_ARN = os.environ.get("MODEL_SECRET_ARN", "")

SUPPORTED_VIDEO_CODECS = {"h264", "hevc", "vp9", "av1"}
SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}

jobs_table = dynamodb.Table(JOBS_TABLE)


def handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    _load_model_secrets()
    failures: list[dict[str, str]] = []
    for record in event.get("Records", []):
        message_id = record["messageId"]
        try:
            payload = json.loads(record["body"])
            _process_message(payload)
        except Exception:
            logger.exception("Worker failed SQS message %s", message_id)
            failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}


def _process_message(payload: dict[str, Any]) -> None:
    job_id = str(payload["job_id"])
    source_bucket = str(payload["source_bucket"])
    source_key = str(payload["source_key"])
    artifact_bucket = str(payload.get("artifact_bucket") or ARTIFACT_BUCKET)

    if not _claim_job(job_id):
        logger.info("Skipping job %s because it is already completed", job_id)
        return

    temp_root = Path(settings.worker_tmp_root) / job_id
    input_dir = temp_root / "input"
    processed_dir = temp_root / "processed"
    source_path = input_dir / f"source{Path(source_key).suffix.lower() or '.bin'}"

    try:
        input_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        _update_job(job_id, current_step="downloading", progress=10)
        s3.download_file(source_bucket, source_key, str(source_path))

        probe = _validate_video(job_id, source_path)
        cleaned = _preprocess_video(job_id=job_id, source_path=source_path, processed_dir=processed_dir, has_audio=probe.has_audio)

        extraction_paths = asyncio.run(
            run_video_extraction_stage(
                job_id=job_id,
                bucket=artifact_bucket,
                clean_video_storage_path=cleaned["video_object_path"],
                clean_audio_storage_path=cleaned.get("audio_object_path", ""),
                finalize_job=False,
                local_video_path_override=cleaned["local_video_path"],
                local_audio_path_override=cleaned.get("local_audio_path"),
                keep_local_artifacts=True,
                upload_artifacts=True,
            )
        )
        vlm_paths = asyncio.run(
            run_vlm_reasoning_stage(
                job_id=job_id,
                bucket=artifact_bucket,
                temporal_segments_storage_path=extraction_paths["temporal_segments_json"],
                local_temporal_segments_path=extraction_paths.get("local_temporal_segments_json"),
                local_audio_path=extraction_paths.get("local_audio_path"),
                local_frame_sampling_path=extraction_paths.get("local_frame_sampling_json"),
                transcription_source_audio_storage_path=extraction_paths.get("source_audio_storage_path", ""),
                reuse_local_segment_frames=True,
                keep_local_artifacts=True,
            )
        )
        result_key = asyncio.run(_run_final_caption_stage(job_id=job_id, bucket=artifact_bucket, vlm_paths=vlm_paths))
        _update_job(
            job_id,
            status="completed",
            current_step="completed",
            progress=100,
            result_key=result_key,
            artifact_paths={**extraction_paths, **vlm_paths, "final_result_json": result_key},
        )
    except Exception as exc:
        _update_job(job_id, status="failed", current_step="failed", error_message=str(exc))
        raise
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _claim_job(job_id: str) -> bool:
    try:
        jobs_table.update_item(
            Key={"job_id": job_id},
            UpdateExpression="SET #status = :processing, current_step = :step, progress = :progress, updated_at = :now ADD attempts :one",
            ConditionExpression="#status <> :completed",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":completed": "completed",
                ":processing": "processing",
                ":step": "processing",
                ":progress": Decimal(5),
                ":one": Decimal(1),
                ":now": _now(),
            },
        )
        return True
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return False


def _validate_video(job_id: str, source_path: Path):
    _update_job(job_id, current_step="validating", progress=20)
    if source_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported video container.")
    if source_path.stat().st_size <= 0:
        raise ValueError("Downloaded video file is empty.")
    if source_path.stat().st_size > settings.max_video_size_mb * 1024 * 1024:
        raise ValueError("Video file exceeds the configured size limit.")

    probe = probe_media(source_path)
    if probe.duration_seconds <= 0 or probe.duration_seconds > settings.max_video_duration_seconds:
        raise ValueError("Video duration is invalid or exceeds the configured limit.")
    if not probe.video_codec or probe.video_codec not in SUPPORTED_VIDEO_CODECS:
        raise ValueError("Unsupported video codec.")
    _update_job(job_id, current_step="validated", progress=30, preprocessing_metadata=probe.__dict__)
    return probe


def _preprocess_video(*, job_id: str, source_path: Path, processed_dir: Path, has_audio: bool) -> dict[str, str]:
    _update_job(job_id, current_step="preprocessing", progress=40)
    normalized_path = processed_dir / "normalized.mp4"
    audio_path = processed_dir / "audio.wav"
    run_command(
        args=[
            settings.ffmpeg_path,
            "-y",
            "-i",
            str(source_path),
            "-c:v",
            "libx264",
            "-r",
            "30",
            "-preset",
            "medium",
            "-movflags",
            "+faststart",
            "-an",
            str(normalized_path),
        ],
        timeout_seconds=settings.ffmpeg_timeout_seconds,
    )
    result = {
        "video_object_path": f"processed/{job_id}/cleaned_video.mp4",
        "local_video_path": str(normalized_path),
    }
    if has_audio:
        run_command(
            args=[
                settings.ffmpeg_path,
                "-y",
                "-i",
                str(source_path),
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
        result["audio_object_path"] = f"processed/{job_id}/cleaned_audio.wav"
        result["local_audio_path"] = str(audio_path)
    return result


async def _run_final_caption_stage(*, job_id: str, bucket: str, vlm_paths: dict[str, Any]) -> str:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for final caption generation.")
    client = OpenAIResponsesClient(
        OpenAIResponsesConfig(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout_seconds=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
            reasoning_effort=settings.openai_reasoning_effort,
            text_verbosity=settings.openai_text_verbosity,
        )
    )
    _, _, uploaded_path = await style_captions(
        client=client,
        model=settings.openai_final_caption_model,
        job_id=job_id,
        bucket=bucket,
        storage_prefix=f"processed/{job_id}",
        global_summary_path=Path(vlm_paths["local_global_factual_summary_json"]),
        global_summary_storage_path=vlm_paths["global_factual_summary_json"],
    )
    return uploaded_path


def _update_job(job_id: str, **fields: Any) -> None:
    fields["updated_at"] = _now()
    names: dict[str, str] = {}
    values: dict[str, Any] = {}
    assignments: list[str] = []
    for key, value in fields.items():
        names[f"#{key}"] = key
        values[f":{key}"] = _to_dynamodb_value(value)
        assignments.append(f"#{key} = :{key}")
    jobs_table.update_item(
        Key={"job_id": job_id},
        UpdateExpression="SET " + ", ".join(assignments),
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=values,
    )


def _load_model_secrets() -> None:
    if not MODEL_SECRET_ARN:
        return
    payload = secretsmanager.get_secret_value(SecretId=MODEL_SECRET_ARN)
    secret = json.loads(payload.get("SecretString") or "{}")
    settings_fields = {
        "FIREWORKS_API_KEY": "fireworks_api_key",
        "GOOGLE_GEMINI_API_KEY": "google_gemini_api_key",
        "OPENAI_API_KEY": "openai_api_key",
    }
    for key in settings_fields:
        if key in secret and not os.environ.get(key):
            os.environ[key] = str(secret[key])
        if key in secret:
            setattr(settings, settings_fields[key], str(secret[key]))


def _to_dynamodb_value(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _to_dynamodb_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_dynamodb_value(item) for item in value]
    return value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
