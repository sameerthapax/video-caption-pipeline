# Worker

Dedicated processing worker scaffold for video normalization, frame extraction, transcription,
description, summarization, and caption styling.

## Structure

```text
pipeline/
  normalize.py
  extract_frames.py
  transcribe.py
  describe_frames.py
  summarize.py
  style.py
  pipeline.py
services/
storage/
models/
main.py
```

## Current Role

- Runs as a separate service from the FastAPI API
- Owns processing orchestration
- Will eventually pull queued jobs, process them, and persist results back to Postgres

## Local Run

From repo root:

```bash
npm run dev:worker
```
