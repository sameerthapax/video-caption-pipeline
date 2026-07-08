insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'videos',
  'videos',
  false,
  52428800,
  array['video/mp4', 'video/quicktime', 'video/webm', 'video/x-matroska', 'audio/wav', 'audio/x-wav', 'application/octet-stream']
)
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;
