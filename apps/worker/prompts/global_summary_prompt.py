from __future__ import annotations

import json

from schemas.segments import TemporalSegmentsArtifact
from schemas.video_memory import VideoMemory
from schemas.vlm import VlmSegmentsArtifact


def build_segment_fusion_prompt(
    *,
    job_id: str,
    segment,
    visual_analysis: dict,
    previous_segment_meta: dict,
) -> str:
    frames_payload = [
        {
            "frame_id": frame.frame_id,
            "timestamp": frame.timestamp,
            "storage_path": frame.storage_path,
            "selection_reasons": frame.selection_reasons,
        }
        for frame in segment.frames
    ]
    transcript_payload = [
        {
            "start": chunk.start,
            "end": chunk.end,
            "text": chunk.text,
            "expressive_transcript": chunk.expressive_transcript,
        }
        for chunk in segment.transcript_chunks
    ]
    return f"""
Create the per-segment ground truth for segment {segment.segment_index + 1} of 5.

Rules:
- Combine the visual analysis, transcript chunks, and current segment frames.
- Use the previous segment metadata only for continuity.
- Keep all claims factual and grounded in visible or spoken evidence.
- Identify whether the same people or objects continue from the previous segment.
- Clearly state scene changes, person changes, object changes, and ongoing actions.
- If uncertain, say so instead of guessing.
- Return JSON only.

Return JSON with exactly this structure:
{json.dumps(_segment_truth_shape(), indent=2)}

Current segment frames:
{json.dumps(frames_payload, indent=2)}

Current segment transcript chunks:
{json.dumps(transcript_payload, indent=2)}

Current segment visual analysis:
{json.dumps(visual_analysis, indent=2)}

Previous segment continuity metadata:
{json.dumps(previous_segment_meta, indent=2)}
""".strip()


def build_global_summary_prompt(
    *,
    job_id: str,
    video_memory: VideoMemory,
    segment_artifact: VlmSegmentsArtifact,
    temporal_segments: TemporalSegmentsArtifact,
) -> str:
    frames_payload = [
        {
            "segment_index": segment.segment_index,
            "frames": [
                {
                    "frame_id": frame.frame_id,
                    "timestamp": frame.timestamp,
                    "storage_path": frame.storage_path,
                }
                for frame in segment.frames
            ],
        }
        for segment in temporal_segments.segments
    ]
    transcript_payload = [
        {
            "segment_index": segment.segment_index,
            "transcript_chunks": [
                {
                    "start": chunk.start,
                    "end": chunk.end,
                    "text": chunk.text,
                    "expressive_transcript": chunk.expressive_transcript,
                }
                for chunk in segment.transcript_chunks
            ],
        }
        for segment in temporal_segments.segments
    ]
    return f"""
Create a factual, style-neutral video description.

Job ID: {job_id}

Rules:
- Use only evidence in video memory, fused per-segment truth, transcript chunks, and provided segment frames.
- Do not be funny or sarcastic.
- Do not invent details.
- Mention setting, subjects, objects, key actions, continuity, scene changes, and transcript-supported context.
- Compare transcript timing, speaking style, tone, and apparent speaker changes against the visual evidence and segment-level visual analysis.
- Be highly detailed because this output is the ground truth source for later caption generation.
- Distinguish what is directly visible, what is directly spoken, and where those two sources align or diverge.
- Identify recurring people, objects, and settings across segments and explain continuity changes.
- If the transcript suggests speech or tone but the visible speaker is uncertain, say that explicitly.
- If multiple people may be present, note whether speaker identity is visually confirmed or unconfirmed.
- If the video has no clear outcome, say what is visible instead of inventing one.
- No audio file is available here. Use only transcript text and prior fused evidence for audio-related statements.
- Return JSON only.

Return JSON with exactly this structure:
{json.dumps(_summary_shape(), indent=2)}

Video memory:
{video_memory.model_dump_json(indent=2)}

Segment reasoning outputs:
{segment_artifact.model_dump_json(indent=2)}

Fused temporal segments ground truth:
{temporal_segments.model_dump_json(indent=2)}

Transcript chunks:
{json.dumps(transcript_payload, indent=2)}

Segment frames:
{json.dumps(frames_payload, indent=2)}
""".strip()


def _summary_shape() -> dict:
    return {
        "factual_summary": "",
        "detailed_ground_truth": "",
        "detailed_timeline": [
            {
                "segment_index": 0,
                "summary": "",
                "key_events": [],
                "visual_facts": [],
                "transcript_facts": [],
                "continuity_notes": [],
            }
        ],
        "main_subjects": [],
        "main_objects": [],
        "setting_summary": "",
        "audio_summary": "",
        "transcript_visual_alignment": [
            {
                "segment_index": 0,
                "transcript_summary": "",
                "visual_alignment": "",
                "speaker_changes": [],
                "tone_notes": [],
                "mismatches_or_uncertainties": [],
            }
        ],
        "speaker_analysis": [
            {
                "speaker_label": "",
                "speaking_style": "",
                "tone_or_emotion": "",
                "evidence": [],
                "appears_across_segments": [],
                "confidence": 0.0,
            }
        ],
        "scene_change_overview": [
            {
                "segment_index": 0,
                "apparent_change": "",
                "related_subjects": [],
                "related_objects": [],
            }
        ],
        "continuity_overview": [
            {
                "segment_index": 0,
                "continuity_note": "",
                "continued_subjects": [],
                "new_subjects": [],
                "continued_objects": [],
                "new_objects": [],
            }
        ],
        "object_and_subject_tracking": [
            {
                "object_id": "",
                "name": "",
                "tracking_summary": "",
                "entity_type": "",
                "appears_across_segments": [],
            }
        ],
        "uncertainties": [],
        "confidence": 0.0,
    }


def _segment_truth_shape() -> dict:
    return {
        "segment_index": 0,
        "start": 0.0,
        "end": 0.0,
        "scene_summary": "",
        "grounded_visual_facts": [],
        "grounded_transcript_facts": [],
        "subjects": [],
        "objects": [],
        "setting": "",
        "scene_change": "",
        "continuity": {
            "same_people": [],
            "new_people": [],
            "same_objects": [],
            "new_objects": [],
            "continuity_notes": [],
        },
        "key_events": [],
        "uncertainties": [],
    }
