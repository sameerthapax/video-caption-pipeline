from prompts.global_summary_prompt import build_global_summary_prompt
from prompts.segment_vlm_prompt import build_segment_vlm_prompt
from schemas.frames import FrameArtifact
from schemas.segments import SamplingConfig, TemporalSegment, TemporalSegmentsArtifact
from schemas.transcription import TranscriptChunk
from schemas.video import VideoMetadata
from schemas.video_memory import VideoMemory, SegmentMemoryEntry
from schemas.vlm import VlmSegmentsArtifact


def test_prompt_includes_current_segment_number_and_previous_memory():
    segment = TemporalSegment(
        segment_index=2,
        start=24.0,
        end=36.0,
        percent_range="40-60",
        frames=[FrameArtifact(frame_id="f1", timestamp=25.0, storage_path="processed/job-1/frames/f1.jpg", local_path="/tmp/f1.jpg")],
        transcript_chunks=[TranscriptChunk(start=24.0, end=29.0, text="hello", expressive_transcript="hello")],
    )
    memory = VideoMemory(
        job_id="job-1",
        segments_processed=2,
        segment_memories=[SegmentMemoryEntry(segment_index=index, memory="previous memory" if index == 1 else "") for index in range(5)],
    )

    prompt = build_segment_vlm_prompt(job_id="job-1", segment=segment, memory=memory)

    assert "segment 3 of 5" in prompt
    assert "previous memory" in prompt


def test_prompt_forbids_hallucination():
    segment = TemporalSegment(segment_index=0, start=0.0, end=12.0, percent_range="0-20")
    memory = VideoMemory(job_id="job-1", segment_memories=[SegmentMemoryEntry(segment_index=index) for index in range(5)])

    prompt = build_segment_vlm_prompt(job_id="job-1", segment=segment, memory=memory)

    assert "Only describe visible or audible evidence" in prompt
    assert "Do not guess missing details" in prompt


def test_global_summary_prompt_does_not_mention_style_captions():
    temporal_segments = TemporalSegmentsArtifact(
        job_id="job-1",
        video_metadata=VideoMetadata(duration=60.0, width=1080, height=1920, fps=30.0),
        sampling_config=SamplingConfig(),
        segments=[],
    )
    prompt = build_global_summary_prompt(
        job_id="job-1",
        video_memory=VideoMemory(job_id="job-1", segment_memories=[SegmentMemoryEntry(segment_index=index) for index in range(5)]),
        segment_artifact=VlmSegmentsArtifact(job_id="job-1"),
        temporal_segments=temporal_segments,
    )

    assert "style-neutral" in prompt
    assert "funny or sarcastic" in prompt
    assert "styled captions" not in prompt


def test_global_summary_prompt_requests_detailed_ground_truth_and_alignment():
    temporal_segments = TemporalSegmentsArtifact(
        job_id="job-1",
        video_metadata=VideoMetadata(duration=60.0, width=1080, height=1920, fps=30.0),
        sampling_config=SamplingConfig(),
        segments=[],
    )
    prompt = build_global_summary_prompt(
        job_id="job-1",
        video_memory=VideoMemory(job_id="job-1", segment_memories=[SegmentMemoryEntry(segment_index=index) for index in range(5)]),
        segment_artifact=VlmSegmentsArtifact(job_id="job-1"),
        temporal_segments=temporal_segments,
    )

    assert "Compare transcript timing, speaking style, tone" in prompt
    assert "detailed_ground_truth" in prompt
    assert "transcript_visual_alignment" in prompt
    assert "speaker_analysis" in prompt
