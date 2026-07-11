resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${local.worker_lambda_name}"
  retention_in_days = var.worker_log_retention_days
}

resource "aws_lambda_function" "worker" {
  count = var.worker_image_uri == "" ? 0 : 1

  function_name = local.worker_lambda_name
  role          = aws_iam_role.worker_lambda.arn
  package_type  = "Image"
  image_uri     = var.worker_image_uri
  timeout       = var.worker_lambda_timeout_seconds
  memory_size   = var.worker_lambda_memory_mb

  reserved_concurrent_executions = var.worker_reserved_concurrency

  ephemeral_storage {
    size = var.worker_ephemeral_storage_mb
  }

  environment {
    variables = {
      AWS_LAMBDA_STORAGE_MODE    = "s3"
      AWS_LAMBDA_JOB_STATUS_MODE = "dynamodb"
      SOURCE_BUCKET              = aws_s3_bucket.source_videos.bucket
      ARTIFACT_BUCKET            = aws_s3_bucket.artifacts.bucket
      JOBS_TABLE                 = aws_dynamodb_table.jobs.name
      MODEL_SECRET_ARN           = var.model_secret_arn
      FIREWORKS_MODEL            = var.fireworks_model
      OPENAI_FINAL_CAPTION_MODEL = var.openai_final_caption_model
      DATABASE_URL               = "sqlite:////tmp/lambda-placeholder.db"
      SUPABASE_URL               = "https://placeholder.invalid"
      SUPABASE_SERVICE_ROLE_KEY  = "placeholder"
      SUPABASE_VIDEO_BUCKET      = aws_s3_bucket.artifacts.bucket
      WORKER_TMP_ROOT            = "/tmp/video-jobs"
      FFMPEG_PATH                = "/usr/bin/ffmpeg"
      FFPROBE_PATH               = "/usr/bin/ffprobe"
      MAX_VIDEO_DURATION_SECONDS = "180"
      MAX_VIDEO_SIZE_MB          = "500"
    }
  }

  depends_on = [aws_cloudwatch_log_group.worker]
}

resource "aws_lambda_event_source_mapping" "worker_sqs" {
  count = var.worker_image_uri == "" ? 0 : 1

  event_source_arn        = aws_sqs_queue.processing.arn
  function_name           = aws_lambda_function.worker[0].arn
  batch_size              = 1
  function_response_types = ["ReportBatchItemFailures"]
}
