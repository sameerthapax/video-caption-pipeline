from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass
from typing import Any

import httpx

from app.core.config import settings


@dataclass(frozen=True)
class WorkerProgressEvent:
    event: str
    job_id: str
    step: str
    message: str
    progress: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def invoke_video_worker(job_id: str) -> AsyncIterator[WorkerProgressEvent]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            settings.worker_invoke_url,
            json={"job_id": job_id},
        )
        response.raise_for_status()
        payload = response.json()

    yield WorkerProgressEvent(
        event=payload["event"],
        job_id=payload["job_id"],
        step=payload["step"],
        message=payload["message"],
        progress=payload.get("progress"),
    )
