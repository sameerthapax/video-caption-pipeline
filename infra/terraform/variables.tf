variable "project_name" {
  description = "Logical project name used by future deployment resources."
  type        = string
  default     = "video-caption-pipeline"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}
