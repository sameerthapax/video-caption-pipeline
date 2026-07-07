# Supabase Integration Plan

## Current Roles

- Postgres: Supabase Postgres is the required application database through `DATABASE_URL`.
- Auth: Supabase Auth now powers backend-owned email/password login, and FastAPI maps authenticated users to `VideoJob.user_id` ownership in the API.
- Storage: Supabase Storage will replace local media writes for uploaded videos and derived assets.
- RLS: Every current table in `public` is expected to run with row level security enabled.

## Environment Variables

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL`

## Local Development

- `DATABASE_URL` is required for the current backend.
- `SUPABASE_URL` and `SUPABASE_ANON_KEY` are required for the current auth flow.
- Uploads are stored locally under `apps/api/media/videos/`.
- Local JWT expiry is set to 1800 seconds in `supabase/config.toml`.
- The web client also signs users out after 30 minutes of inactivity to keep the session window aligned with the intended ideal state.

## Current Auth Flow

1. The React app calls FastAPI auth endpoints for signup, login, logout, and session checks.
2. FastAPI exchanges credentials with Supabase Auth and stores the returned session tokens in HTTP-only cookies.
3. Protected frontend requests send cookies only to FastAPI with `credentials: include`, and unsafe requests also send `X-CSRF-Token` from the readable CSRF cookie.
4. FastAPI validates or refreshes the Supabase session server-side, then loads the user identity.
5. Job upload, status, and result endpoints only operate on rows where `video_jobs.user_id` matches the authenticated user.

## Current Middleware Security

- `CORSMiddleware` allows only configured origins and credentialed requests.
- `TrustedHostMiddleware` restricts inbound `Host` headers to `ALLOWED_HOSTS`.
- `CSRFMiddleware` blocks unsafe cookie-authenticated requests unless the CSRF cookie matches `X-CSRF-Token`.
- `RateLimitMiddleware` applies Redis-backed per-IP throttles to login, signup, and upload endpoints.

## Current Public-Schema RLS

- `public.video_jobs` is protected by authenticated-user policies keyed on `user_id = auth.uid()::text`.
- `public.video_caption_results` is protected through ownership of the parent job row.
- `ALTER TABLE ... FORCE ROW LEVEL SECURITY` is applied to both tables.
- The policies are defined in [supabase/migrations/20260707000200_enable_public_table_rls.sql](/Users/sams/Desktop/video-caption-pipeline/supabase/migrations/20260707000200_enable_public_table_rls.sql:1).
- FastAPI also reapplies the same RLS DDL at startup after `create_all()` so app-created tables do not come up without policies.

## TODO

- Move uploaded files from local disk to Supabase Storage.
- Switch the production database connection to Supabase Postgres.
