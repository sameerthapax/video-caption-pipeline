from __future__ import annotations


def transcribe_audio(job_id: str) -> dict[str, str]:
    return {"job_id": job_id, "step": "transcribing_audio"}
