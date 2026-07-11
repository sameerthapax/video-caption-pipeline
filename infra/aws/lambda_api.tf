data "archive_file" "api_lambda" {
  type        = "zip"
  source_dir  = "${path.module}/lambda/api"
  output_path = "${path.module}/api-lambda.zip"
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${local.api_lambda_name}"
  retention_in_days = var.api_log_retention_days
}

resource "aws_lambda_function" "api" {
  function_name    = local.api_lambda_name
  role             = aws_iam_role.api_lambda.arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.api_lambda.output_path
  source_code_hash = data.archive_file.api_lambda.output_base64sha256
  timeout          = var.api_lambda_timeout_seconds
  memory_size      = var.api_lambda_memory_mb

  environment {
    variables = {
      SOURCE_BUCKET        = aws_s3_bucket.source_videos.bucket
      ARTIFACT_BUCKET      = aws_s3_bucket.artifacts.bucket
      JOBS_TABLE           = aws_dynamodb_table.jobs.name
      PROCESSING_QUEUE_URL = aws_sqs_queue.processing.url
      PRESIGN_EXPIRES_IN   = "900"
    }
  }

  depends_on = [aws_cloudwatch_log_group.api]
}
