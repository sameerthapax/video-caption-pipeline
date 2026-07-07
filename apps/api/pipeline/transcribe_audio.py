from time import sleep


def transcribe_audio(video_path: str) -> dict:
    sleep(1)
    # TODO: Integrate Fireworks AI or another ASR provider here.
    return {
        "transcript": "Placeholder transcript for local development.",
        "confidence": 0.93,
    }
