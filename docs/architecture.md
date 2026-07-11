# Architecture Notes

## Monorepo Layout

- `apps/web`: React + TypeScript frontend served by Vite and orchestrated through Nx targets.
- `apps/api`: FastAPI + SQLAlchemy backend for auth, persistence, and API routing.
- `apps/worker`: Dedicated processing worker for media preprocessing, extraction, and hierarchical VLM reasoning.
- `libs/shared-types`: Shared frontend TypeScript API contracts.
- `docs`: Human-readable architecture and integration notes.
- `infra/terraform`: Minimal deployment scaffold for future cloud work.

## Request Flow

1. User uploads a short video in the web client.
2. Frontend posts metadata to `POST /api/videos/upload/` and receives a signed Supabase Storage upload URL plus the object path for a pending `VideoJob`.
3. Frontend uploads the file directly to the private `videos` bucket, then calls `POST /api/videos/upload/complete/stream`.
4. FastAPI verifies the stored object metadata, marks the job `queued`, invokes the worker through a dedicated HTTP invoker abstraction, and streams progress via SSE.
5. The worker service runs as a separate process, receives the invocation on its own port, normalizes and validates media, extracts frames, builds temporal segments, and then runs sequential segment-level VLM reasoning with accumulated video memory.
6. The worker uploads extraction artifacts and VLM artifacts back to Supabase Storage, while updating durable job state in Postgres.
7. Frontend still polls `GET /api/jobs/{job_id}/status/` for durable job state while also reflecting the immediate SSE progress stream.
8. Final styled caption generation remains future work; the current AI pipeline stops at `global_factual_summary.json`.

## Immediate Tradeoffs

- Supabase Postgres is the required database via `DATABASE_URL`.
- Worker orchestration is implemented as an API-invoked HTTP worker that performs preprocessing, extraction, transcription windowing, temporal segmentation, and hierarchical VLM reasoning.
- SQLAlchemy `create_all()` initializes current tables on startup for speed; FastAPI immediately reapplies the current Supabase RLS policy set after table creation so public tables are not left unsecured.
- Security middleware is intentionally lightweight and app-local right now: Redis-backed rate limiting, CSRF validation for cookie-authenticated writes, `TrustedHostMiddleware`, and configured CORS.
- Shared types currently cover the frontend only; backend contracts and artifact expectations are documented in `docs/api-contract.md` and `apps/worker/README.md`.
- Supabase Auth is required, and Supabase Storage now owns browser-direct video uploads; production should still point `DATABASE_URL` at Supabase Postgres so Storage verification and job metadata live in the same project.
