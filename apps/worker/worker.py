from __future__ import annotations

from pydantic import BaseModel, Field

from pipeline.run_extraction_stage import run_video_extraction_stage
from pipeline.run_vlm_stage import run_vlm_reasoning_stage


class VideoExtractionStageRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=36)
    clean_video_storage_path: str = Field(min_length=1)
    clean_audio_storage_path: str = Field(default="")
    bucket: str = Field(min_length=1)


class VideoExtractionStageResponse(BaseModel):
    job_id: str
    current_step: str
    progress: int
    artifact_paths: dict


async def run_extraction_stage_request(payload: VideoExtractionStageRequest) -> VideoExtractionStageResponse:
    artifact_paths = await run_video_extraction_stage(
        job_id=payload.job_id,
        bucket=payload.bucket,
        clean_video_storage_path=payload.clean_video_storage_path,
        clean_audio_storage_path=payload.clean_audio_storage_path,
    )
    return VideoExtractionStageResponse(
        job_id=payload.job_id,
        current_step="extraction_completed",
        progress=100,
        artifact_paths=artifact_paths,
    )


class VideoVlmReasoningStageRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=36)
    bucket: str = Field(min_length=1)
    temporal_segments_storage_path: str = Field(min_length=1)


class VideoVlmReasoningStageResponse(BaseModel):
    job_id: str
    current_step: str
    progress: int
    artifact_paths: dict


async def run_vlm_reasoning_stage_request(payload: VideoVlmReasoningStageRequest) -> VideoVlmReasoningStageResponse:
    artifact_paths = await run_vlm_reasoning_stage(
        job_id=payload.job_id,
        bucket=payload.bucket,
        temporal_segments_storage_path=payload.temporal_segments_storage_path,
    )
    return VideoVlmReasoningStageResponse(
        job_id=payload.job_id,
        current_step="vlm_reasoning_completed",
        progress=100,
        artifact_paths=artifact_paths,
    )
