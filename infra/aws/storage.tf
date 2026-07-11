resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "source_videos" {
  bucket = "${local.name_prefix}-source-videos-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket" "artifacts" {
  bucket = "${local.name_prefix}-artifacts-${random_id.bucket_suffix.hex}"
}

resource "aws_s3_bucket_public_access_block" "source_videos" {
  bucket                  = aws_s3_bucket.source_videos.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "source_videos" {
  bucket = aws_s3_bucket.source_videos.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "source_videos" {
  bucket = aws_s3_bucket.source_videos.id
  rule {
    id     = "delete-temporary-source-videos"
    status = "Enabled"
    filter {
      prefix = "uploads/"
    }
    expiration {
      days = var.source_video_retention_days
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  rule {
    id     = "delete-processing-artifacts"
    status = "Enabled"
    filter {
      prefix = "processed/"
    }
    expiration {
      days = var.artifact_retention_days
    }
  }
}

resource "aws_s3_bucket_cors_configuration" "source_videos" {
  bucket = aws_s3_bucket.source_videos.id
  cors_rule {
    allowed_headers = ["content-type", "x-amz-*"]
    allowed_methods = ["PUT"]
    allowed_origins = var.allowed_frontend_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 300
  }
}
