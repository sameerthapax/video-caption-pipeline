from pipeline.video_memory import create_video_memory, merge_segment_into_memory
from schemas.frames import FrameArtifact
from schemas.segments import TemporalSegment
from schemas.vlm import SegmentVlmResponse


def test_memory_has_five_segment_slots():
    memory = create_video_memory(job_id="job-1")
    assert len(memory.segment_memories) == 5
    assert [entry.segment_index for entry in memory.segment_memories] == [0, 1, 2, 3, 4]


def test_memory_merge_preserves_subject_ids():
    memory = create_video_memory(job_id="job-1")
    segment = TemporalSegment(
        segment_index=1,
        start=12.0,
        end=24.0,
        percent_range="20-40",
        frames=[FrameArtifact(frame_id="f1", timestamp=13.0, storage_path="processed/job-1/frames/f1.jpg", local_path="/tmp/f1.jpg")],
        transcript_chunks=[],
    )
    response = SegmentVlmResponse.model_validate(
        {
            "segment_index": 1,
            "segment_start": 12.0,
            "segment_end": 24.0,
            "subjects": [
                {
                    "subject_id": "person_99",
                    "is_new": True,
                    "matched_previous_subject_id": "person_1",
                    "type": "person",
                    "appearance": {"visible_features": ["long hair"], "clothing": ["red shirt"], "colors": ["red"], "accessories": [], "pose_or_posture": "", "confidence": 0.8},
                    "actions": ["walking"],
                    "movement": "moves left",
                    "facial_expression": "",
                    "emotion_or_tone": {"label": "", "evidence": "", "confidence": 0.0},
                    "state_change": "",
                    "confidence": 0.85,
                }
            ],
        }
    )

    merge_segment_into_memory(memory=memory, segment=segment, response=response)

    assert [item.subject_id for item in memory.persistent_subjects] == ["person_1"]
    assert memory.persistent_subjects[0].first_seen_segment == 1
