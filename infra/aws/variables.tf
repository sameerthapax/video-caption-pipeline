variable "aws_region" {
  description = "AWS region for all resources."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project tag and resource name prefix."
  type        = string
  default     = "video-caption-pipeline"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "github_owner" {
  description = "GitHub organization or user that owns the repository."
  type        = string
  default     = "sameerthapax"
}

variable "github_repository" {
  description = "GitHub repository name."
  type        = string
  default     = "video-caption-pipeline"
}

variable "github_branch" {
  description = "Branch Amplify should build automatically."
  type        = string
  default     = "main"
}

variable "github_access_token" {
  description = "Optional Amplify GitHub access token. Prefer authorizing the Amplify GitHub App instead of storing this in Terraform state."
  type        = string
  default     = null
  sensitive   = true
}

variable "allowed_frontend_origins" {
  description = "Allowed browser origins for API Gateway CORS and S3 presigned uploads."
  type        = list(string)
  default     = ["http://localhost:5173"]
}

variable "source_video_retention_days" {
  description = "Number of days to retain uploaded source videos."
  type        = number
  default     = 3
  validation {
    condition     = var.source_video_retention_days >= 1 && var.source_video_retention_days <= 30
    error_message = "source_video_retention_days must be between 1 and 30."
  }
}

variable "artifact_retention_days" {
  description = "Number of days to retain processed artifacts/results."
  type        = number
  default     = 7
  validation {
    condition     = var.artifact_retention_days >= 1 && var.artifact_retention_days <= 90
    error_message = "artifact_retention_days must be between 1 and 90."
  }
}

variable "enable_dynamodb_pitr" {
  description = "Enable DynamoDB point-in-time recovery."
  type        = bool
  default     = false
}

variable "api_log_retention_days" {
  description = "CloudWatch log retention for API Lambda."
  type        = number
  default     = 7
}

variable "worker_log_retention_days" {
  description = "CloudWatch log retention for worker Lambda."
  type        = number
  default     = 7
}

variable "api_lambda_timeout_seconds" {
  description = "API Lambda timeout."
  type        = number
  default     = 30
}

variable "api_lambda_memory_mb" {
  description = "API Lambda memory size."
  type        = number
  default     = 256
}

variable "worker_image_uri" {
  description = "Immutable worker Lambda image URI, usually ECR repo URL plus a git SHA tag. Leave empty until the first image is pushed."
  type        = string
  default     = ""
}

variable "worker_lambda_timeout_seconds" {
  description = "Worker Lambda timeout. Must be no more than the Lambda maximum of 900 seconds."
  type        = number
  default     = 900
  validation {
    condition     = var.worker_lambda_timeout_seconds >= 60 && var.worker_lambda_timeout_seconds <= 900
    error_message = "worker_lambda_timeout_seconds must be between 60 and 900."
  }
}

variable "worker_lambda_memory_mb" {
  description = "Worker Lambda memory size."
  type        = number
  default     = 2048
}

variable "worker_ephemeral_storage_mb" {
  description = "Worker Lambda /tmp storage size."
  type        = number
  default     = 4096
  validation {
    condition     = var.worker_ephemeral_storage_mb >= 512 && var.worker_ephemeral_storage_mb <= 10240
    error_message = "worker_ephemeral_storage_mb must be between 512 and 10240."
  }
}

variable "worker_reserved_concurrency" {
  description = "Reserved concurrency cap for the worker Lambda. Use a low value in dev to prevent cost spikes."
  type        = number
  default     = 2
}

variable "queue_max_receive_count" {
  description = "SQS receives before a message is moved to the dead-letter queue."
  type        = number
  default     = 3
}

variable "model_secret_arn" {
  description = "Optional Secrets Manager secret ARN containing model provider API keys. Prefer creating it outside Terraform."
  type        = string
  default     = ""
  sensitive   = true
}

variable "fireworks_model" {
  description = "Fireworks model name used by the worker."
  type        = string
  default     = ""
}

variable "openai_final_caption_model" {
  description = "OpenAI model used for final captions."
  type        = string
  default     = "gpt-5.5"
}

variable "budget_email" {
  description = "Optional email address for a low monthly AWS Budget alert. Empty disables budget creation."
  type        = string
  default     = ""
}

variable "budget_monthly_limit_usd" {
  description = "Monthly budget threshold in USD when budget_email is set."
  type        = number
  default     = 10
}
