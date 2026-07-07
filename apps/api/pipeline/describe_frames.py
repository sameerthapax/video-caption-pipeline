from time import sleep


def describe_frames(video_path: str) -> dict:
    sleep(1)
    # TODO: Replace with a vision model call for actual scene descriptions.
    return {
        "descriptions": [
            "A person speaks directly to camera.",
            "Subtitles and screen motion suggest a demo or tutorial clip.",
        ]
    }
