# Video Caption Pipeline

Hackathon-ready monorepo skeleton for uploading short videos with a dedicated API app and a separate processing worker app.

## Project Overview

- Monorepo manager: Nx
- Frontend: React + TypeScript with Vite
- Backend API: FastAPI + SQLAlchemy
- Worker: Python processing service scaffold
- Database/Auth/Storage: Supabase
- Infra scaffold: Terraform
- CI scaffold: GitHub Actions

The current implementation is intentionally simple: local file uploads, Supabase-backed Postgres via `DATABASE_URL`, a structured FastAPI API app for auth and persistence, and a separate worker scaffold for future processing orchestration.

For local data services, the repo now uses the existing `supabase/` project with a pruned CLI stack that keeps:

- Studio
- Postgres
- Auth
- Storage

And excludes:

- Realtime
- ImgProxy
- Mailpit
- Edge Runtime
- Logflare
- Vector service
- Supavisor

`pgvector` is initialized as a Postgres extension, not as a separate container.

## Architecture Diagram

```text
apps/web (React + TS)
  -> POST /api/videos/upload/
  -> PUT signed Supabase Storage upload URL
  -> POST /api/videos/upload/complete/
  -> poll GET /api/jobs/{job_id}/status/
  -> GET /api/jobs/{job_id}/result/

apps/api (FastAPI)
  -> creates signed upload target and owns auth/session state
  -> verifies uploaded storage object
  -> returns job/result state from Postgres

apps/worker (Python worker)
  -> claims processing jobs
  -> runs normalize/extract/transcribe/describe/summarize/style steps
  -> writes result state back to Postgres

libs/shared-types
  -> shared frontend API types

docs/
  -> architecture, API contract, Supabase plan

infra/terraform
  -> minimal deployment scaffold
```

## Repository Layout

```text
apps/
  web/                  React + TypeScript frontend
  api/                  FastAPI auth + persistence API
  worker/               Processing worker scaffold
libs/
  shared-types/         Shared frontend TypeScript contracts
docs/                   Architecture and API docs
infra/
  terraform/            Minimal Terraform scaffold
.github/
  workflows/ci.yml      Minimal CI workflow
```

## Setup Instructions

### 1. Install dependencies

Node dependencies:

```bash
npm install
```

Python dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r apps/api/requirements.txt
```

### 2. Configure environment variables

Copy the example file and adjust values as needed:

```bash
cp .env.example .env
```

Important variables:

- `VITE_API_BASE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `REDIS_KEY_PREFIX`
- `APP_ENV`
- `APP_DEBUG`
- `CORS_ALLOWED_ORIGINS`

`DATABASE_URL` is required.

For the local Supabase stack, start from `.env.example`. The important local defaults are:

- `SUPABASE_URL=http://127.0.0.1:54321`
- `DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:54322/postgres`
- `REDIS_URL=redis://127.0.0.1:6379/0`

After starting Supabase, replace the placeholder auth keys with the output of:

```bash
npm run supabase:env
```

The frontend only needs `VITE_API_BASE_URL`. FastAPI owns the Supabase auth credentials and is the only layer that talks to Supabase Auth.

### 3. Prepare the backend database

Start the local Supabase stack first:

```bash
npm run supabase:start
```

Then load the generated environment values you need and start the API. The FastAPI app creates its current tables on startup:

```bash
source venv/bin/activate
npm run dev:api
```

### 4. Run local development

Backend only:

```bash
source venv/bin/activate
npm run dev:api
```

Worker only:

```bash
source venv/bin/activate
npm run dev:worker
```

Redis only for backend development:

```bash
npm run redis:start
```

API + worker + Redis in containers:

```bash
npm run dev:stack
```

Frontend only:

```bash
npm run dev:web
```

Frontend + backend:

```bash
source venv/bin/activate
npm run dev
```

Auth behavior:

- Email/password login and signup are handled by FastAPI, which proxies requests to Supabase Auth.
- The browser only talks to FastAPI and uses HTTP-only auth cookies.
- Authenticated `POST` requests also require the `X-CSRF-Token` header that matches the `vp_csrf_token` cookie.
- Browser sessions are signed out after 30 minutes of inactivity in the client.
- Local Supabase JWT expiry is configured to 30 minutes in [supabase/config.toml](/Users/sams/Desktop/video-caption-pipeline/supabase/config.toml:1).

Security middleware:

- CORS is restricted to configured origins in `CORS_ALLOWED_ORIGINS`.
- Trusted hosts are restricted by `ALLOWED_HOSTS`.
- Cookie-authenticated unsafe requests are protected by CSRF middleware.
- Login, signup, and upload endpoints have Redis-backed per-IP rate limits.
- HTTPS redirect middleware can be enabled outside local development with `APP_FORCE_HTTPS=true`.

### 5. Run with Docker Compose

For local container-based testing:

```bash
npm run supabase:start
docker compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Worker: separate background container, no public port

Notes:

- The backend container starts FastAPI with Uvicorn.
- `DATABASE_URL` points from the backend container to the local Supabase Postgres port on the host.
- Uploaded videos go directly from the browser to the Supabase Storage `videos` bucket with a signed upload URL.
- The frontend container runs the Vite dev server so UI behavior stays easy to test locally.
- If you want to change API or CORS settings, update `.env` before starting Compose.

## Development Commands

- `npm run dev:web`: Start the React frontend on port `5173`
- `npm run dev:api`: Start the FastAPI backend on port `8000`
- `npm run dev:worker`: Start the worker scaffold locally
- `npm run dev`: Run frontend, API, and worker together
- `npm run dev:stack`: Start API, worker, and Redis together with Docker Compose
- `npm run redis:start`: Start the local Redis container
- `npm run redis:stop`: Stop the local Redis container
- `npm run supabase:start`: Start the pruned local Supabase stack
- `npm run supabase:stop`: Stop the local Supabase stack
- `npm run supabase:status`: Show local Supabase service status
- `npm run supabase:env`: Print local Supabase URLs and keys as env lines
- `npm run lint`: Lint the frontend and shared TypeScript library
- `npm run typecheck:web`: Typecheck the frontend
- `npm run check:api`: Import and validate the FastAPI application
- `npm run test:web`: Run frontend tests with Vitest
- `npm run test:api`: Run FastAPI backend tests
- `npm run test`: Run frontend and backend tests
- `docker compose up --build`: Run frontend and backend in local containers

## API Endpoints

- `POST /api/auth/signup/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `GET /api/auth/session/`
- `POST /api/videos/upload/` (requires auth cookie)
- `POST /api/videos/upload/complete/` (requires auth cookie)
- `GET /api/jobs/{job_id}/status/` (requires auth cookie, owner only)
- `GET /api/jobs/{job_id}/result/` (requires auth cookie, owner only)

Detailed payload examples live in [docs/api-contract.md](/Users/sams/Desktop/video-caption-pipeline/docs/api-contract.md).

## API Structure

The backend now lives under a layered structure in [apps/api/README.md](/Users/sams/Desktop/video-caption-pipeline/apps/api/README.md:1):

- middleware
- endpoints
- controllers
- services
- models
- utils
- tests

The processing flow now belongs under [apps/worker/README.md](/Users/sams/Desktop/video-caption-pipeline/apps/worker/README.md:1), not inside the API route layer.

## Supabase

Supabase is currently used for:

- Postgres database
- Auth scaffolding
- Storage scaffolding

Details live in [docs/supabase.md](/Users/sams/Desktop/video-caption-pipeline/docs/supabase.md) and [docs/supabase-local.md](/Users/sams/Desktop/video-caption-pipeline/docs/supabase-local.md).

## Future Deployment Plan

- Frontend deployed as a cloud function/service
- Backend deployed as a cloud function/service
- Terraform extended from the current scaffold in `infra/terraform`
- CI expanded from `.github/workflows/ci.yml`
- Implement real job claiming and persistence inside `apps/worker`
- Add production-oriented container images and image publishing once the target runtime is chosen
