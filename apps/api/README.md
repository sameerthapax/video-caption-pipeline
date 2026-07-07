# API

FastAPI auth, persistence, and routing service for the video-caption pipeline monorepo.

## Structure

```text
app/
  api/
    endpoints/      Route handlers only
    router.py       API router assembly
  controllers/      HTTP-facing orchestration layer
  core/             Config and database bootstrapping
  middleware/       Cross-cutting request middleware
  models/           SQLAlchemy models
  schemas/          Pydantic request/response schemas
  services/         Business logic and persistence workflows
  utils/            File and helper utilities
tests/              Backend tests
```

## Current Endpoints

- `GET /healthz`
- `POST /api/videos/upload/`
- `GET /api/jobs/{job_id}/status/`
- `GET /api/jobs/{job_id}/result/`

## Design Notes

- The API does not own media processing logic.
- Upload currently stores the file locally and creates a `VideoJob` in status `uploaded`.
- Result retrieval returns `409` until the worker service creates a `VideoCaptionResult`.
- Tables are initialized on startup with SQLAlchemy metadata for speed during scaffolding.

## Local Run

From repo root:

```bash
npm run dev:api
```

To run Redis for rate limiting locally:

```bash
npm run redis:start
```

To run the full API/worker/Redis container stack:

```bash
npm run dev:stack
```

Directly:

```bash
cd apps/api
../../venv/bin/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Tests

From repo root:

```bash
npm run test:api
```

## Next Steps

- Add Alembic for explicit schema migrations
- Replace local media writes with Supabase Storage
