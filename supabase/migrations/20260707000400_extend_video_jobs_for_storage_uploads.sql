alter table public.video_jobs
  add column if not exists storage_bucket text not null default 'videos',
  add column if not exists upload_content_type text not null default 'application/octet-stream',
  add column if not exists upload_file_size integer not null default 0;

alter table public.video_jobs
  alter column status set default 'pending_upload',
  alter column current_step set default 'awaiting_upload';

update public.video_jobs
set
  storage_bucket = coalesce(storage_bucket, 'videos'),
  upload_content_type = coalesce(upload_content_type, 'application/octet-stream'),
  upload_file_size = coalesce(upload_file_size, 0)
where
  storage_bucket is null
  or upload_content_type is null
  or upload_file_size is null;
