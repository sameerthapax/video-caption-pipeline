# Video Caption Pipeline

Hackathon-ready monorepo skeleton for uploading short videos, running a placeholder backend processing pipeline, and rendering captions in four tones on the frontend.

## Project Overview

- Monorepo manager: Nx
- Frontend: React + TypeScript with Vite
- Backend: Django + Django REST Framework
- Database/Auth/Storage: Supabase
- Infra scaffold: Terraform
- CI scaffold: GitHub Actions

The current implementation is intentionally simple: local file uploads, Supabase-backed Postgres via `DATABASE_URL`, and a background thread that simulates the future AI pipeline without adding queues or orchestration yet.

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
  -> poll GET /api/jobs/{job_id}/status/
  -> GET /api/jobs/{job_id}/result/

apps/api (Django + DRF)
  -> stores upload under apps/api/media/videos/
  -> creates VideoJob
  -> runs placeholder pipeline thread
  -> saves VideoCaptionResult

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
  api/                  Django backend and placeholder pipeline
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
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DJANGO_CORS_ALLOWED_ORIGINS`

`DATABASE_URL` is required.

For the local Supabase stack, start from `.env.example`. The important local defaults are:

- `SUPABASE_URL=http://127.0.0.1:54321`
- `DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:54322/postgres`

After starting Supabase, replace the placeholder auth keys with the output of:

```bash
npm run supabase:env
```

### 3. Prepare the backend database

Start the local Supabase stack first:

```bash
npm run supabase:start
```

Then load the generated environment values you need and run Django migrations:

```bash
source venv/bin/activate
python apps/api/manage.py migrate
```

### 4. Run local development

Backend only:

```bash
source venv/bin/activate
npm run dev:api
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

### 5. Run with Docker Compose

For local container-based testing:

```bash
npm run supabase:start
docker compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

Notes:

- The backend container runs `migrate` on startup, then starts Django.
- `DATABASE_URL` points from the backend container to the local Supabase Postgres port on the host.
- Uploaded videos are stored in a Docker volume mounted at `/app/media`.
- The frontend container runs the Vite dev server so UI behavior stays easy to test locally.
- If you want to change API or CORS settings, update `.env` before starting Compose.

## Development Commands

- `npm run dev:web`: Start the React frontend on port `5173`
- `npm run dev:api`: Start the Django backend on port `8000`
- `npm run dev`: Run frontend and backend together
- `npm run supabase:start`: Start the pruned local Supabase stack
- `npm run supabase:stop`: Stop the local Supabase stack
- `npm run supabase:status`: Show local Supabase service status
- `npm run supabase:env`: Print local Supabase URLs and keys as env lines
- `npm run lint`: Lint the frontend and shared TypeScript library
- `npm run typecheck:web`: Typecheck the frontend
- `npm run check:api`: Run Django system checks
- `npm run test:web`: Run frontend tests with Vitest
- `npm run test:api`: Run Django tests
- `npm run test`: Run all configured tests through Nx
- `docker compose up --build`: Run frontend and backend in local containers

## API Endpoints

- `POST /api/videos/upload/`
- `GET /api/jobs/{job_id}/status/`
- `GET /api/jobs/{job_id}/result/`

Detailed payload examples live in [docs/api-contract.md](/Users/sams/Desktop/video-caption-pipeline/docs/api-contract.md).

## Pipeline Placeholder

The backend currently simulates these steps:

1. `uploaded`
2. `normalizing_video`
3. `extracting_frames`
4. `transcribing_audio`
5. `describing_frames`
6. `generating_neutral_summary`
7. `generating_styled_captions`
8. `completed`

Placeholder services live in:

- `apps/api/pipeline/normalize_video.py`
- `apps/api/pipeline/extract_frames.py`
- `apps/api/pipeline/transcribe_audio.py`
- `apps/api/pipeline/describe_frames.py`
- `apps/api/pipeline/neutral_summary.py`
- `apps/api/pipeline/styled_captions.py`
- `apps/api/pipeline/run_pipeline.py`

TODOs are marked where real Fireworks AI, Supabase Storage, and production-grade processing should be integrated.

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
- Replace the thread placeholder with a durable job system once the hackathon prototype proves the flow
- Add production-oriented container images and image publishing once the target runtime is chosen
