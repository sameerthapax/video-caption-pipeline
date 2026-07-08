from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import asdict, dataclass
import json
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
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


async def invoke_video_worker(job_id: str) -> AsyncIterator[WorkerProgressEvent]:
    timeout = httpx.Timeout(connect=10.0, read=None, write=30.0, pool=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            settings.worker_invoke_url,
            json={"job_id": job_id},
        ) as response:
            response.raise_for_status()
            async for event in _iter_sse_events(response):
                yield event


async def _iter_sse_events(response: httpx.Response) -> AsyncIterator[WorkerProgressEvent]:
    event_name: str | None = None
    data_lines: list[str] = []

    async for raw_line in response.aiter_lines():
        line = raw_line.strip()
        if not line:
            if event_name and data_lines:
                payload = json.loads("\n".join(data_lines))
                yield WorkerProgressEvent(
                    event=payload["event"] if "event" in payload else event_name,
                    job_id=payload["job_id"],
                    step=payload["step"],
                    message=payload["message"],
                    progress=payload.get("progress"),
                    metadata=payload.get("metadata"),
                )
            event_name = None
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.removeprefix("event:").strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())

    if event_name and data_lines:
        payload = json.loads("\n".join(data_lines))
        yield WorkerProgressEvent(
            event=payload["event"] if "event" in payload else event_name,
            job_id=payload["job_id"],
            step=payload["step"],
            message=payload["message"],
            progress=payload.get("progress"),
            metadata=payload.get("metadata"),
        )
