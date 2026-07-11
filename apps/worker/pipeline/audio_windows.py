from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from core.config import settings
from schemas.transcription import TranscriptChunk
from services.process import run_command


@dataclass(frozen=True)
class AudioWindowFile:
    start: float
    end: float
    path: Path
    mime_type: str = "audio/wav"


def build_transcript_windows(duration: float, window_seconds: float = 5.0) -> list[TranscriptChunk]:
    if duration <= 0:
        return []
    window_count = max(1, int(math.ceil(duration / window_seconds)))
    windows: list[TranscriptChunk] = []
    for index in range(window_count):
        start = round(index * window_seconds, 4)
        end = round(min(duration, start + window_seconds), 4)
        windows.append(TranscriptChunk(start=start, end=end))
    return windows


def extract_audio_window_files(
    *,
    source_audio_path: Path,
    output_dir: Path,
    transcript_windows: list[TranscriptChunk],
) -> list[AudioWindowFile]:
    output_dir.mkdir(parents=True, exist_ok=True)
    window_files: list[AudioWindowFile] = []
    for index, window in enumerate(transcript_windows):
        duration = max(window.end - window.start, 0.1)
        window_path = output_dir / f"window_{index:03d}_{window.start:.2f}s_{window.end:.2f}s.wav"
        run_command(
            args=[
                settings.ffmpeg_path,
                "-y",
                "-ss",
                str(window.start),
                "-i",
                str(source_audio_path),
                "-t",
                str(duration),
                "-ac",
                "1",
                "-ar",
                "24000",
                "-c:a",
                "pcm_s16le",
                str(window_path),
            ],
            timeout_seconds=settings.ffmpeg_timeout_seconds,
        )
        window_files.append(AudioWindowFile(start=window.start, end=window.end, path=window_path))
    return window_files
