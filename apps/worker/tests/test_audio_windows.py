from pipeline.audio_windows import build_transcript_windows


def test_build_transcript_windows_uses_five_second_chunks():
    windows = build_transcript_windows(duration=12.0, window_seconds=5.0)

    assert [(window.start, window.end) for window in windows] == [
        (0.0, 5.0),
        (5.0, 10.0),
        (10.0, 12.0),
    ]

