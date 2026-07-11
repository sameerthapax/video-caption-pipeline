do $$
begin
  if to_regclass('public.video_jobs') is null then
    return;
  end if;

  execute $sql$
    alter table public.video_jobs
      add column if not exists processing_started_at timestamptz,
      add column if not exists preprocessing_metadata jsonb not null default '{}'::jsonb,
      add column if not exists artifact_paths jsonb not null default '{}'::jsonb
  $sql$;
end
$$;
