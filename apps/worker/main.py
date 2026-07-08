from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import SessionLocal
from services.events import WorkerProgressEvent, format_sse_event
from services.processor import process_video_job

logger = logging.getLogger("video-caption-pipeline.worker")

app = FastAPI(
    title="Video Caption Pipeline Worker",
    version="0.1.0",
    description="Dedicated worker process invoked over HTTP by the API service.",
)


class WorkerInvokeRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=36)


class WorkerInvokeResponse(BaseModel):
    event: str
    job_id: str
    step: str
    message: str
    progress: int | None = None
    metadata: dict | None = None


@app.post("/invoke/video-job")
async def invoke_video_job(payload: WorkerInvokeRequest) -> StreamingResponse:
    def event_stream() -> iter[str]:
        db: Session = SessionLocal()
        try:
            for event in process_video_job(db=db, job_id=payload.job_id):
                yield format_sse_event(event)
        finally:
            db.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
