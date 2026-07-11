from schemas.vlm import GlobalFactualSummary


def test_global_summary_schema_normalizes_mixed_inputs_to_typed_models():
    payload = {
        "factual_summary": "A screen recording shows a user editing visuals and browsing websites.",
        "scene_change_overview": [
            {"segment_index": 0, "apparent_change": "The view switches from an editing interface to a desktop."},
            {"segment_index": 1, "summary": "The screen changes to a browser page."},
        ],
        "continuity_overview": [
            "The same on-screen workflow continues across adjacent segments.",
        ],
        "object_and_subject_tracking": [
            {"object_id": "person_1", "tracking_summary": "The same cursor-driven workflow continues across segments."},
            {"object_id": "object_1", "name": "cursor"},
        ],
    }

    summary = GlobalFactualSummary.model_validate(payload)

    assert summary.scene_change_overview[0].apparent_change == "The view switches from an editing interface to a desktop."
    assert summary.scene_change_overview[1].apparent_change == "The screen changes to a browser page."
    assert summary.continuity_overview[0].continuity_note == "The same on-screen workflow continues across adjacent segments."
    assert summary.object_and_subject_tracking[0].tracking_summary == "The same cursor-driven workflow continues across segments."
    assert summary.object_and_subject_tracking[1].tracking_summary == "cursor"
