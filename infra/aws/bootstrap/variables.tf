variable "aws_region" {
  description = "AWS region for bootstrap resources."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for bootstrap resource names."
  type        = string
  default     = "video-caption-pipeline"
}

variable "environment" {
  description = "Environment name."
  type        = string
  default     = "dev"
}

variable "github_owner" {
  description = "Exact GitHub owner or organization."
  type        = string
}

variable "github_repository" {
  description = "Exact GitHub repository name."
  type        = string
}

variable "github_environment" {
  description = "GitHub Environment allowed to assume the deployment role."
  type        = string
  default     = "development"
}
