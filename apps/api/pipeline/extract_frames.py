from time import sleep


def extract_frames(video_path: str) -> dict:
    sleep(1)
    # TODO: Replace with actual frame sampling for multimodal analysis.
    return {"frame_count": 12, "frame_manifest": [f"{video_path}:frame-{index}" for index in range(1, 4)]}
