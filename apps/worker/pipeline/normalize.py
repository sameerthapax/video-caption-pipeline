from __future__ import annotations


def normalize_video(job_id: str) -> dict[str, str]:
    return {"job_id": job_id, "step": "normalizing_video"}
