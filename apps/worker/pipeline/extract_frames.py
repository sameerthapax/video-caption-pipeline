from __future__ import annotations


def extract_frames(job_id: str) -> dict[str, str]:
    return {"job_id": job_id, "step": "extracting_frames"}
