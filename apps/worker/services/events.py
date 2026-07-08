from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class WorkerProgressEvent:
    event: str
    job_id: str
    step: str
    message: str
    progress: int | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if payload["metadata"] is None:
            payload.pop("metadata")
        return payload


def format_sse_event(progress_event: WorkerProgressEvent) -> str:
    return f"event: {progress_event.event}\ndata: {json.dumps(progress_event.to_dict())}\n\n"
