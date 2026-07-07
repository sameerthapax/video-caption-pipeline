# API Contract

## `POST /api/videos/upload/`

Creates a pending upload job and returns a signed Supabase Storage upload URL.

Request:

- JSON body:

```json
{
  "filename": "demo.mp4",
  "content_type": "video/mp4",
  "file_size": 1048576
}
```

Response `202 Accepted`:

```json
{
  "job_id": "0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7",
  "status": "pending_upload",
  "bucket": "videos",
  "object_path": "user-id/0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7/demo.mp4",
  "upload_url": "http://127.0.0.1:54321/storage/v1/object/upload/sign/videos/user-id/0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7/demo.mp4?token=...",
  "upload_method": "PUT",
  "upload_headers": {
    "Content-Type": "video/mp4"
  }
}
```

## `POST /api/videos/upload/complete/`

Confirms the browser upload finished and asks the backend to verify the object metadata in Supabase Storage.

Request:

```json
{
  "job_id": "0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7",
  "object_path": "user-id/0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7/demo.mp4",
  "file_size": 1048576,
  "content_type": "video/mp4"
}
```

Response `200 OK`:

```json
{
  "job_id": "0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7",
  "status": "uploaded",
  "verified": true
}
```

## `POST /api/videos/upload/complete/stream`

Confirms the browser upload finished, verifies the stored object, marks the job `queued`, invokes the worker through the API-side worker invoker abstraction, and streams progress updates as SSE.

Request:

```json
{
  "job_id": "0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7",
  "object_path": "user-id/0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7/demo.mp4",
  "file_size": 1048576,
  "content_type": "video/mp4"
}
```

Response `200 OK` with `Content-Type: text/event-stream`:

```text
event: queued
data: {"event":"queued","job_id":"0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7","step":"queued","message":"Upload verified and job queued.","progress":15}

event: worker_invoked
data: {"event":"worker_invoked","job_id":"0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7","step":"worker_invocation","message":"Worker invocation accepted.","progress":20}

event: worker_available
data: {"event":"worker_available","job_id":"0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7","step":"worker_available","message":"Worker sees queued job 0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7 as available.","progress":15}
```

## `GET /api/jobs/{job_id}/status/`

Response `200 OK`:

```json
{
  "id": "0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7",
  "status": "processing",
  "current_step": "transcribing_audio",
  "progress": 45,
  "error_message": "",
  "original_filename": "demo.mp4",
  "created_at": "2026-07-06T20:00:00Z",
  "updated_at": "2026-07-06T20:00:05Z"
}
```

## `GET /api/jobs/{job_id}/result/`

Response `200 OK`:

```json
{
  "job_id": "0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7",
  "neutral_summary": "Neutral summary text",
  "formal_caption": "Formal caption text",
  "sarcastic_caption": "Sarcastic caption text",
  "humorous_tech_caption": "Humorous tech caption text",
  "humorous_non_tech_caption": "Humorous non-tech caption text",
  "raw_output_json": {},
  "created_at": "2026-07-06T20:00:15Z"
}
```

## Notes

- `409 Conflict` on the result endpoint means the job exists but output is not ready yet.
- `409 Conflict` on `POST /api/videos/upload/complete/` means the backend could not match the uploaded object metadata with the prepared job.
- `POST /api/videos/upload/complete/stream` emits `failed` as an SSE event when invocation fails after the stream has started.
- `404 Not Found` is returned when the job ID does not exist.
- The frontend maps the snake_case API fields into camelCase client types.
- The browser uploads the file directly to Supabase Storage with the signed URL and then calls either the normal completion endpoint or the SSE completion endpoint.
- The API surface is worker-agnostic: processing happens in the separate worker service, not inside FastAPI.
- The current worker stub only acknowledges that the queued job is visible; it does not mark the job `processing` or `completed`.
