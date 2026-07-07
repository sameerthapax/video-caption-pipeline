from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

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


@app.post("/invoke/video-job", response_model=WorkerInvokeResponse)
async def invoke_video_job(payload: WorkerInvokeRequest) -> WorkerInvokeResponse:
    logger.info("Worker received job %s", payload.job_id)
    logger.info("Worker sees queued job %s as available", payload.job_id)
    return WorkerInvokeResponse(
        event="worker_available",
        job_id=payload.job_id,
        step="worker_available",
        message=f"Worker sees queued job {payload.job_id} as available.",
        progress=15,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
