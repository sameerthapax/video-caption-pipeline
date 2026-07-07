# Local Supabase Setup

## Goal

Keep the local Supabase stack limited to the parts this repo actually needs right now:

- Studio
- Postgres
- Auth
- Storage

## Important Detail

There is no separate `pgvector` container to pull.

`pgvector` is a PostgreSQL extension that is enabled inside the local Supabase Postgres database by:

- `supabase/migrations/20260707000100_enable_pgvector.sql`

## Commands

Start the minimal local stack:

```bash
npm run supabase:start
```

Stop it:

```bash
npm run supabase:stop
```

Inspect generated local URLs and keys:

```bash
npm run supabase:env
```

## Services We Intentionally Exclude

- `realtime`
- `imgproxy`
- `mailpit`
- `edge-runtime`
- `logflare`
- `vector`
- `supavisor`

## Services We Still Keep As Supporting Dependencies

- `kong`
- `postgrest`
- `postgres-meta`

These are kept because Studio and the standard local Supabase API surface depend on them in practice. This is an inference from the current Supabase CLI service model and config surface, not a published dependency table.

## Local Environment Notes

For browser-based frontend access:

- `SUPABASE_URL=http://127.0.0.1:54321`

For the backend container talking to local Supabase on the host:

- `DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:54322/postgres`

If your local Supabase credentials differ, use the values emitted by:

```bash
npm run supabase:env
```
