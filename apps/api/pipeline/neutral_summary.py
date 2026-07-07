from time import sleep


def generate_neutral_summary(transcript: str, frame_descriptions: list[str]) -> str:
    sleep(1)
    joined = " ".join(frame_descriptions)
    return (
        "The clip shows a short talk-to-camera moment with supporting visual activity. "
        f"Transcript seed: {transcript} Visual seed: {joined}"
    )
