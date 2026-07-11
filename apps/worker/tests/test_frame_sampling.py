from pipeline.frame_sampling import (
    TimestampCandidate,
    dedupe_timestamp_candidates,
    generate_safety_timestamps,
    generate_uniform_timestamps,
)
from pipeline.scene_change import select_scene_change_indices


def test_generate_uniform_timestamps_evenly_spaced():
    timestamps = generate_uniform_timestamps(duration=20.0, count=4)

    assert timestamps == [0.5, 6.8333, 13.1667, 19.5]


def test_generate_safety_timestamps_uses_expected_positions():
    timestamps = generate_safety_timestamps(duration=30.0)

    assert timestamps == [0.5, 9.9, 19.8, 29.5]


def test_dedupe_timestamp_candidates_merges_close_matches():
    merged, decisions = dedupe_timestamp_candidates(
        candidates=[
            TimestampCandidate(timestamp=0.5, reason="uniform"),
            TimestampCandidate(timestamp=0.7, reason="safety"),
            TimestampCandidate(timestamp=4.2, reason="scene_change", scene_change_score=0.8),
        ],
        threshold_seconds=0.5,
    )

    assert len(merged) == 2
    assert merged[0].reasons == {"uniform", "safety"}
    assert merged[1].scene_change_score == 0.8
    assert len(decisions) == 1
    assert decisions[0].reason == "timestamp_within_threshold"


def test_dedupe_replaces_duplicates_from_rejected_scene_change_pool():
    merged, decisions = dedupe_timestamp_candidates(
        candidates=[
            TimestampCandidate(timestamp=0.5, reason="uniform"),
            TimestampCandidate(timestamp=0.7, reason="safety"),
            TimestampCandidate(timestamp=4.2, reason="scene_change", scene_change_score=0.8),
        ],
        threshold_seconds=0.5,
        replacement_candidates=[
            TimestampCandidate(timestamp=0.9, reason="scene_change_replacement", scene_change_score=0.2),
            TimestampCandidate(timestamp=1.4, reason="scene_change_replacement", scene_change_score=0.9),
            TimestampCandidate(timestamp=7.0, reason="scene_change_replacement", scene_change_score=0.7),
        ],
        target_count=3,
    )

    assert [round(item.timestamp, 1) for item in merged] == [0.5, 1.4, 4.2]
    assert any(decision.reason == "replaced_with_rejected_scene_change" for decision in decisions)


def test_dedupe_backfills_to_target_count_from_rejected_scene_change_pool():
    merged, decisions = dedupe_timestamp_candidates(
        candidates=[
            TimestampCandidate(timestamp=0.5, reason="uniform"),
            TimestampCandidate(timestamp=0.7, reason="safety"),
            TimestampCandidate(timestamp=4.2, reason="scene_change", scene_change_score=0.8),
        ],
        threshold_seconds=0.5,
        replacement_candidates=[
            TimestampCandidate(timestamp=1.4, reason="scene_change_replacement", scene_change_score=0.9),
            TimestampCandidate(timestamp=7.0, reason="scene_change_replacement", scene_change_score=0.8),
            TimestampCandidate(timestamp=11.5, reason="scene_change_replacement", scene_change_score=0.7),
        ],
        target_count=4,
    )

    assert len(merged) == 4
    assert [round(item.timestamp, 1) for item in merged] == [0.5, 1.4, 4.2, 7.0]
    assert any(decision.reason == "filled_from_rejected_scene_change_pool" for decision in decisions)


def test_scene_change_selection_respects_minimum_spacing():
    timestamps = [0.5, 1.5, 2.5, 4.5, 8.5, 12.5]
    scores = [0.1, 0.9, 0.8, 0.7, 1.0, 0.95]

    selected = select_scene_change_indices(
        timestamps=timestamps,
        scores=scores,
        min_spacing_seconds=4.0,
        max_selected=8,
    )

    assert selected == [1, 4, 5]
