# Architecture Notes

## Monorepo Layout

- `apps/web`: React + TypeScript frontend served by Vite and orchestrated through Nx targets.
- `apps/api`: FastAPI + SQLAlchemy backend for auth, persistence, and API routing.
- `apps/worker`: Dedicated processing worker for media and caption generation steps.
- `libs/shared-types`: Shared frontend TypeScript API contracts.
- `docs`: Human-readable architecture and integration notes.
- `infra/terraform`: Minimal deployment scaffold for future cloud work.

## Request Flow

1. User uploads a short video in the web client.
2. Frontend posts the file to `POST /api/videos/upload/`.
3. FastAPI stores the file, creates a `VideoJob`, and exposes job state through Postgres-backed endpoints.
4. The worker service claims queued jobs, runs processing steps, and persists a `VideoCaptionResult`.
5. Frontend polls `GET /api/jobs/{job_id}/status/` every two seconds until the job completes.
6. Frontend loads `GET /api/jobs/{job_id}/result/` and displays the neutral summary plus the four caption variants.

## Immediate Tradeoffs

- Supabase Postgres is the required database via `DATABASE_URL`.
- Worker orchestration is scaffolded but not implemented yet; the worker app is currently a container and module layout with placeholder functions.
- SQLAlchemy `create_all()` initializes current tables on startup for speed; FastAPI immediately reapplies the current Supabase RLS policy set after table creation so public tables are not left unsecured.
- Security middleware is intentionally lightweight and app-local right now: Redis-backed rate limiting, CSRF validation for cookie-authenticated writes, `TrustedHostMiddleware`, and configured CORS.
- Shared types currently cover the frontend only; backend contracts are documented in `docs/api-contract.md`.
- Supabase Auth and Storage are still planned, but only Postgres is required right now.
