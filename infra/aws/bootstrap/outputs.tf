output "state_bucket" {
  description = "S3 bucket for Terraform remote state."
  value       = aws_s3_bucket.state.bucket
}

output "github_actions_role_arn" {
  description = "Role ARN to store as GitHub Actions variable AWS_ROLE_ARN."
  value       = aws_iam_role.github_deploy.arn
}

output "state_lock_table" {
  description = "DynamoDB table for Terraform S3 backend locking."
  value       = aws_dynamodb_table.state_lock.name
}
