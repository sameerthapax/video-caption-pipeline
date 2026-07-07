from __future__ import annotations


def summarize_content(job_id: str) -> dict[str, str]:
    return {"job_id": job_id, "step": "generating_neutral_summary"}
