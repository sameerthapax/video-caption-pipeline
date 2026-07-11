from __future__ import annotations

import json
import mimetypes
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3

s3 = boto3.client("s3")
sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")

SOURCE_BUCKET = os.environ["SOURCE_BUCKET"]
ARTIFACT_BUCKET = os.environ["ARTIFACT_BUCKET"]
JOBS_TABLE = os.environ["JOBS_TABLE"]
PROCESSING_QUEUE_URL = os.environ["PROCESSING_QUEUE_URL"]
PRESIGN_EXPIRES_IN = int(os.environ.get("PRESIGN_EXPIRES_IN", "900"))

jobs_table = dynamodb.Table(JOBS_TABLE)


def handler(event: dict[str, Any], _context: object) -> dict[str, Any]:
    route_key = event.get("routeKey", "")
    path_params = event.get("pathParameters") or {}

    try:
        if route_key == "POST /uploads/presign":
            return _json_response(_presign_upload(_json_body(event)))
        if route_key == "POST /jobs":
            return _json_response(_create_job(_json_body(event)), status_code=201)
        if route_key == "GET /jobs/{job_id}":
            return _json_response(_get_job(path_params["job_id"]))
        if route_key == "GET /jobs/{job_id}/result":
            return _json_response(_get_result(path_params["job_id"]))
        return _json_response({"error": "not_found"}, status_code=404)
    except KeyError as exc:
        return _json_response({"error": "missing_field", "field": str(exc)}, status_code=400)
    except ValueError as exc:
        return _json_response({"error": "bad_request", "message": str(exc)}, status_code=400)


def _presign_upload(body: dict[str, Any]) -> dict[str, Any]:
    filename = str(body["filename"]).strip()
    content_type = str(body.get("content_type") or mimetypes.guess_type(filename)[0] or "application/octet-stream")
    if not filename:
        raise ValueError("filename is required")
    if not content_type.startswith("video/") and content_type not in {"application/octet-stream"}:
        raise ValueError("content_type must be a video content type")

    job_id = str(body.get("job_id") or uuid.uuid4())
    extension = os.path.splitext(filename)[1].lower() or ".bin"
    object_key = f"uploads/{job_id}/source{extension}"
    upload_url = s3.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": SOURCE_BUCKET,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=PRESIGN_EXPIRES_IN,
    )
    return {
        "job_id": job_id,
        "bucket": SOURCE_BUCKET,
        "object_key": object_key,
        "upload_url": upload_url,
        "expires_in": PRESIGN_EXPIRES_IN,
        "headers": {"Content-Type": content_type},
    }


def _create_job(body: dict[str, Any]) -> dict[str, Any]:
    job_id = str(body["job_id"])
    source_key = str(body["source_key"])
    original_filename = str(body.get("filename") or os.path.basename(source_key))
    content_type = str(body.get("content_type") or "video/*")
    now = _now()

    if not source_key.startswith(f"uploads/{job_id}/"):
        raise ValueError("source_key must match uploads/{job_id}/...")

    s3.head_object(Bucket=SOURCE_BUCKET, Key=source_key)
    item = {
        "job_id": job_id,
        "status": "queued",
        "current_step": "queued",
        "progress": Decimal(0),
        "source_bucket": SOURCE_BUCKET,
        "source_key": source_key,
        "artifact_bucket": ARTIFACT_BUCKET,
        "result_key": f"processed/{job_id}/final_result.json",
        "original_filename": original_filename,
        "content_type": content_type,
        "created_at": now,
        "updated_at": now,
        "attempts": Decimal(0),
    }
    jobs_table.put_item(
        Item=item,
        ConditionExpression="attribute_not_exists(job_id)",
    )
    sqs.send_message(
        QueueUrl=PROCESSING_QUEUE_URL,
        MessageBody=json.dumps(
            {
                "job_id": job_id,
                "source_bucket": SOURCE_BUCKET,
                "source_key": source_key,
                "artifact_bucket": ARTIFACT_BUCKET,
            }
        ),
    )
    return _normalize_item(item)


def _get_job(job_id: str) -> dict[str, Any]:
    item = _load_job(job_id)
    return _normalize_item(item)


def _get_result(job_id: str) -> dict[str, Any]:
    item = _load_job(job_id)
    if item.get("status") != "completed":
        return {
            "job_id": job_id,
            "status": item.get("status"),
            "result": None,
        }

    result_key = str(item.get("result_key") or f"processed/{job_id}/final_result.json")
    result_object = s3.get_object(Bucket=ARTIFACT_BUCKET, Key=result_key)
    result = json.loads(result_object["Body"].read().decode("utf-8"))
    return {
        "job_id": job_id,
        "status": "completed",
        "result_key": result_key,
        "result": result,
    }


def _load_job(job_id: str) -> dict[str, Any]:
    response = jobs_table.get_item(Key={"job_id": job_id})
    item = response.get("Item")
    if not item:
        raise ValueError("job not found")
    return item


def _json_body(event: dict[str, Any]) -> dict[str, Any]:
    raw_body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        raise ValueError("base64 request bodies are not supported")
    body = json.loads(raw_body)
    if not isinstance(body, dict):
        raise ValueError("JSON body must be an object")
    return body


def _json_response(payload: dict[str, Any], status_code: int = 200) -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload, default=_json_default),
    }


def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(item, default=_json_default))


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
