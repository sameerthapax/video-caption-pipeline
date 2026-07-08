alter table public.video_jobs
  add column if not exists processing_started_at timestamptz,
  add column if not exists preprocessing_metadata jsonb not null default '{}'::jsonb;
