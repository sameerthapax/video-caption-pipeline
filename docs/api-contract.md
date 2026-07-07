# API Contract

## `POST /api/videos/upload/`

Uploads a single video file as multipart form-data.

Request:

- Field: `video`

Response `202 Accepted`:

```json
{
  "job_id": "0d3ae1fb-13f8-4eb8-9896-0d4f327c6bc7",
  "status": "uploaded"
}
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
- `404 Not Found` is returned when the job ID does not exist.
- The frontend maps the snake_case API fields into camelCase client types.
- The API surface is worker-agnostic: processing happens in the separate worker service, not inside FastAPI.
