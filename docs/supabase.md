# Supabase Integration Plan

## Current Roles

- Postgres: Supabase Postgres is the required application database through `DATABASE_URL`.
- Auth: Supabase Auth will map authenticated users to future `VideoJob.user_id` ownership and access control.
- Storage: Supabase Storage will replace local media writes for uploaded videos and derived assets.

## Environment Variables

- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL`

## Local Development

- `DATABASE_URL` is required for the current backend.
- You do not need Auth or Storage credentials yet unless you start integrating those pieces.
- Uploads are stored locally under `apps/api/media/videos/`.

## TODO

- Add Supabase Auth session validation in Django once protected routes matter.
- Move uploaded files from local disk to Supabase Storage.
- Switch the production database connection to Supabase Postgres.
