from time import sleep


def generate_styled_captions(summary: str) -> dict:
    sleep(1)
    # TODO: Replace with LLM prompt templates once the real caption generation layer is ready.
    return {
        "formal_caption": f"Formal: {summary}",
        "sarcastic_caption": f"Sarcastic: Another extremely normal video moment. {summary}",
        "humorous_tech_caption": f"Humorous tech: The clip shipped to production with zero unit tests. {summary}",
        "humorous_non_tech_caption": f"Humorous non-tech: Main character energy, but with subtitles. {summary}",
    }
