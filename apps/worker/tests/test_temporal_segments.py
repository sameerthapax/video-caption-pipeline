from pipeline.temporal_segments import (
    assign_frames_to_segments,
    assign_transcript_chunks_to_segments,
    build_segment_boundaries,
)
from schemas.frames import FrameArtifact
from schemas.transcription import TranscriptChunk


def test_build_segment_boundaries_creates_five_ranges():
    boundaries = build_segment_boundaries(duration=60.0, segment_count=5)

    assert boundaries == [
        (0.0, 12.0, "0-20"),
        (12.0, 24.0, "20-40"),
        (24.0, 36.0, "40-60"),
        (36.0, 48.0, "60-80"),
        (48.0, 60.0, "80-100"),
    ]


def test_assign_frames_to_segments_places_by_timestamp():
    frames = [
        FrameArtifact(frame_id="frame_00", timestamp=0.5, storage_path="a", local_path="/tmp/a"),
        FrameArtifact(frame_id="frame_01", timestamp=15.0, storage_path="b", local_path="/tmp/b"),
        FrameArtifact(frame_id="frame_02", timestamp=59.0, storage_path="c", local_path="/tmp/c"),
    ]

    buckets = assign_frames_to_segments(frames=frames, duration=60.0, segment_count=5)

    assert [frame.frame_id for frame in buckets[0]] == ["frame_00"]
    assert [frame.frame_id for frame in buckets[1]] == ["frame_01"]
    assert [frame.frame_id for frame in buckets[4]] == ["frame_02"]


def test_assign_transcript_chunks_to_segments_uses_overlap():
    chunks = [
        TranscriptChunk(start=0.0, end=5.0),
        TranscriptChunk(start=10.0, end=15.0),
        TranscriptChunk(start=50.0, end=55.0),
    ]

    buckets = assign_transcript_chunks_to_segments(transcript_chunks=chunks, duration=60.0, segment_count=5)

    assert [(chunk.start, chunk.end) for chunk in buckets[0]] == [(0.0, 5.0), (10.0, 15.0)]
    assert [(chunk.start, chunk.end) for chunk in buckets[1]] == [(10.0, 15.0)]
    assert [(chunk.start, chunk.end) for chunk in buckets[4]] == [(50.0, 55.0)]

