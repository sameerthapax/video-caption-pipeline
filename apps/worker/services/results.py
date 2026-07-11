from __future__ import annotations

from sqlalchemy.orm import Session

from models.job import VideoCaptionResult, VideoJob
from schemas.vlm import FinalCaptionResult


def upsert_caption_result(*, db: Session, job: VideoJob, final_result: FinalCaptionResult) -> VideoCaptionResult:
    result = db.query(VideoCaptionResult).filter(VideoCaptionResult.job_id == job.id).one_or_none()
    if result is None:
        result = VideoCaptionResult(job_id=job.id)

    result.neutral_summary = final_result.neutral_summary
    result.formal_caption = final_result.formal_caption
    result.sarcastic_caption = final_result.sarcastic_caption
    result.humorous_tech_caption = final_result.humorous_tech_caption
    result.humorous_non_tech_caption = final_result.humorous_non_tech_caption
    result.raw_output_json = final_result.model_dump(mode="json")

    db.add(result)
    db.commit()
    db.refresh(result)
    return result
