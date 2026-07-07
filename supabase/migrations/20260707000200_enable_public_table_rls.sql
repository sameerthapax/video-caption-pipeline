do $$
begin
  if to_regclass('public.video_jobs') is not null then
    execute 'alter table public.video_jobs enable row level security';
    execute 'alter table public.video_jobs force row level security';

    execute 'drop policy if exists "video_jobs_select_own" on public.video_jobs';
    execute 'create policy "video_jobs_select_own" on public.video_jobs
      for select
      to authenticated
      using (user_id = (select auth.uid())::text)';

    execute 'drop policy if exists "video_jobs_insert_own" on public.video_jobs';
    execute 'create policy "video_jobs_insert_own" on public.video_jobs
      for insert
      to authenticated
      with check (user_id = (select auth.uid())::text)';

    execute 'drop policy if exists "video_jobs_update_own" on public.video_jobs';
    execute 'create policy "video_jobs_update_own" on public.video_jobs
      for update
      to authenticated
      using (user_id = (select auth.uid())::text)
      with check (user_id = (select auth.uid())::text)';

    execute 'drop policy if exists "video_jobs_delete_own" on public.video_jobs';
    execute 'create policy "video_jobs_delete_own" on public.video_jobs
      for delete
      to authenticated
      using (user_id = (select auth.uid())::text)';
  end if;

  if to_regclass('public.video_caption_results') is not null then
    execute 'alter table public.video_caption_results enable row level security';
    execute 'alter table public.video_caption_results force row level security';

    execute 'drop policy if exists "video_caption_results_select_own" on public.video_caption_results';
    execute 'create policy "video_caption_results_select_own" on public.video_caption_results
      for select
      to authenticated
      using (
        exists (
          select 1
          from public.video_jobs
          where public.video_jobs.id = public.video_caption_results.job_id
            and public.video_jobs.user_id = (select auth.uid())::text
        )
      )';

    execute 'drop policy if exists "video_caption_results_insert_own" on public.video_caption_results';
    execute 'create policy "video_caption_results_insert_own" on public.video_caption_results
      for insert
      to authenticated
      with check (
        exists (
          select 1
          from public.video_jobs
          where public.video_jobs.id = public.video_caption_results.job_id
            and public.video_jobs.user_id = (select auth.uid())::text
        )
      )';

    execute 'drop policy if exists "video_caption_results_update_own" on public.video_caption_results';
    execute 'create policy "video_caption_results_update_own" on public.video_caption_results
      for update
      to authenticated
      using (
        exists (
          select 1
          from public.video_jobs
          where public.video_jobs.id = public.video_caption_results.job_id
            and public.video_jobs.user_id = (select auth.uid())::text
        )
      )
      with check (
        exists (
          select 1
          from public.video_jobs
          where public.video_jobs.id = public.video_caption_results.job_id
            and public.video_jobs.user_id = (select auth.uid())::text
        )
      )';

    execute 'drop policy if exists "video_caption_results_delete_own" on public.video_caption_results';
    execute 'create policy "video_caption_results_delete_own" on public.video_caption_results
      for delete
      to authenticated
      using (
        exists (
          select 1
          from public.video_jobs
          where public.video_jobs.id = public.video_caption_results.job_id
            and public.video_jobs.user_id = (select auth.uid())::text
        )
      )';
  end if;
end
$$;
