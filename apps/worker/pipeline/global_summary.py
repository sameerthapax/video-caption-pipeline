from __future__ import annotations

import logging

from prompts.global_summary_prompt import build_global_summary_prompt, build_segment_fusion_prompt
from schemas.segments import TemporalSegmentsArtifact
from schemas.video_memory import VideoMemory
from schemas.vlm import GlobalFactualSummary, VlmSegmentsArtifact
from services.fireworks_client import FireworksClient, FireworksResponseFormatError

logger = logging.getLogger("video-caption-pipeline.worker")


async def generate_global_summary(
    *,
    client: FireworksClient,
    model: str,
    job_id: str,
    video_memory: VideoMemory,
    segment_artifact: VlmSegmentsArtifact,
    temporal_segments: TemporalSegmentsArtifact,
    all_frame_paths: list[str],
) -> GlobalFactualSummary:
    prompt = build_global_summary_prompt(
        job_id=job_id,
        video_memory=video_memory,
        segment_artifact=segment_artifact,
        temporal_segments=temporal_segments,
    )
    try:
        payload = await client.analyze_segment_with_images(
            model=model,
            prompt=prompt,
            image_paths=all_frame_paths,
            temperature=0.1,
        )
        return GlobalFactualSummary.model_validate(payload)
    except FireworksResponseFormatError as exc:
        logger.warning("Global summary JSON parse failed for job %s; attempting repair.", job_id)
        repaired = await client.generate_json(
            model=model,
            prompt=f"Repair this output into valid JSON without adding facts. Return JSON only.\n\n{exc.raw_text}",
            temperature=0.0,
        )
        return GlobalFactualSummary.model_validate(repaired)


async def fuse_segment_ground_truth(
    *,
    client: FireworksClient,
    model: str,
    job_id: str,
    segment,
    visual_response: dict,
    previous_segment_meta: dict,
) -> dict:
    prompt = build_segment_fusion_prompt(
        job_id=job_id,
        segment=segment,
        visual_analysis=visual_response,
        previous_segment_meta=previous_segment_meta,
    )
    return await client.analyze_segment_with_images(
        model=model,
        prompt=prompt,
        image_paths=[frame.local_path for frame in segment.frames if frame.local_path],
        temperature=0.1,
    )
