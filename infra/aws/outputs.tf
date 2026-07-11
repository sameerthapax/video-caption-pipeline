output "api_url" {
  description = "HTTP API invoke URL."
  value       = aws_apigatewayv2_stage.default.invoke_url
}

output "amplify_app_id" {
  description = "Amplify app ID."
  value       = aws_amplify_app.frontend.id
}

output "source_video_bucket" {
  description = "Private source video bucket name."
  value       = aws_s3_bucket.source_videos.bucket
}

output "artifact_bucket" {
  description = "Private artifact/result bucket name."
  value       = aws_s3_bucket.artifacts.bucket
}

output "jobs_table_name" {
  description = "DynamoDB jobs table name."
  value       = aws_dynamodb_table.jobs.name
}

output "processing_queue_url" {
  description = "SQS processing queue URL."
  value       = aws_sqs_queue.processing.url
}

output "worker_ecr_repository_url" {
  description = "ECR repository URL for the worker Lambda image."
  value       = aws_ecr_repository.worker.repository_url
}

output "api_ecr_repository_url" {
  description = "ECR repository URL for the API container image."
  value       = aws_ecr_repository.api.repository_url
}

output "worker_lambda_name" {
  description = "Worker Lambda function name. Empty until worker_image_uri is set."
  value       = var.worker_image_uri == "" ? "" : aws_lambda_function.worker[0].function_name
}
