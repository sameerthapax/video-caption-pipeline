from __future__ import annotations


def style_captions(job_id: str) -> dict[str, str]:
    return {"job_id": job_id, "step": "generating_styled_captions"}
