from time import sleep


def normalize_video(video_path: str) -> dict:
    sleep(1)
    # TODO: Replace with a real normalization/transcoding step, likely ffmpeg-driven.
    return {"normalized_video_path": video_path, "codec": "placeholder-h264"}
