# Worker

The worker now includes two downstream stages after clean video/audio preprocessing:

- extraction and temporal segmentation
- hierarchical VLM reasoning that stops at a factual global summary

## Extraction Stage

Input payload:

```json
{
  "job_id": "...",
  "clean_video_storage_path": "...",
  "clean_audio_storage_path": "...",
  "bucket": "..."
}
```

Outputs uploaded to Supabase Storage:

- `processed/{job_id}/frames/*.jpg`
- `processed/{job_id}/frame_sampling.json`
- `processed/{job_id}/temporal_segments.json`
- `processed/{job_id}/transcription_request.json`

## Hierarchical VLM Reasoning

Input artifact:

- `processed/{job_id}/temporal_segments.json`

Outputs uploaded to Supabase Storage:

- `processed/{job_id}/vlm_segments.json`
- `processed/{job_id}/video_memory.json`
- `processed/{job_id}/global_factual_summary.json`

Architecture:

- extract selected frames and segment boundaries first
- start a visual-only segment analysis branch and a transcript generation branch in parallel
- keep stateful visual memory across segments so later visual prompts can reference the same people, objects, setting, and scene continuity
- upload `vlm_segments.json` after the visual-only branch completes
- upload `transcription_request.json` after the transcript branch completes
- fuse visual analysis, transcript chunks, current segment frames, and previous-segment continuity metadata into per-segment ground truth
- upload fused `temporal_segments.json` and `video_memory.json` after per-segment fusion completes
- run one final global truth call from fused evidence plus segment frames, without passing the raw audio file
- upload `global_factual_summary.json` only after the final global truth is fully materialized

Why segment-level processing is used:

- it keeps each VLM request bounded while still preserving local temporal context
- it reduces frame-by-frame fragmentation and makes continuity matching more stable
- it allows stateful reasoning across the full video without forcing the model to ingest every frame at once

Memory update strategy:

- the visual-only branch returns a structured `memory_update_for_next_segment`
- the worker merges that into persistent subjects, persistent objects, global setting, timeline, and unresolved uncertainties
- previously known IDs are preserved when the model marks a subject or object as matching earlier segments
- all 5 segment memory slots are stored separately so later stages can inspect segment-local state without losing the global view
- fused per-segment ground truth also carries previous-segment metadata such as last frame, last transcript chunk, and last segment summary for continuity

## Frame Sampling

- Probe video metadata with `ffprobe`
- Build empty 5-second transcript windows for the future async transcription stage
- Select 8 uniform frames, 8 scene-change frames, and 4 safety frames
- Scene-change scoring currently uses HSV histogram change plus grayscale pixel change
- A TODO placeholder is left for local CLIP/SigLIP or Fireworks-compatible embedding scoring
- Dedupe timestamps within 0.5 seconds while preserving selection reasons

## JSON Artifacts

- `transcription_request.json`: Google Gemini transcription artifact with 5-second transcript chunks, music metadata, and tone metadata
- `frame_sampling.json`: raw/normalized/smoothed scene scores, selected scene-change frames, final frame list, dedupe decisions
- `temporal_segments.json`: video metadata, sampling config, 5 temporal segments, assigned frames, transcript chunks, VLM placeholders
- `vlm_segments.json`: per-segment inputs plus validated/fallback VLM JSON responses and segment errors
- `video_memory.json`: accumulated state across all 5 temporal segments
- `global_factual_summary.json`: final factual video description, timeline, subjects, objects, audio summary, and uncertainties

## Model Integrations

- `services/google_gemini_client.py` handles transcription for 5-second audio windows
- `services/fireworks_client.py` handles Fireworks OpenAI-compatible calls for segment reasoning and global factual summarization
- `services/openai_responses_client.py` handles the final styled caption stage through the OpenAI Responses API
- `FIREWORKS_MODEL` remains the Fireworks model env var for segment reasoning and global factual summarization
- `OPENAI_FINAL_CAPTION_MODEL` defaults to `gpt-5.5` for the final styled caption bundle

## Local Run

From repo root:

```bash
npm run dev:worker
```

HTTP endpoint:

- `POST /invoke/video-job`

The current worker flow preprocesses the upload, continues into extraction artifacts, and can now continue into hierarchical VLM reasoning until `global_factual_summary.json` is produced.
