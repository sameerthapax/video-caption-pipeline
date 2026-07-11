resource "aws_iam_role" "api_lambda" {
  name = "${local.name_prefix}-api-lambda"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "api_lambda" {
  name = "${local.name_prefix}-api-lambda"
  role = aws_iam_role.api_lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.api.arn}:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.source_videos.arn}/uploads/*",
          "${aws_s3_bucket.artifacts.arn}/processed/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem"
        ]
        Resource = aws_dynamodb_table.jobs.arn
      },
      {
        Effect   = "Allow"
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.processing.arn
      }
    ]
  })
}

resource "aws_iam_role" "worker_lambda" {
  name = "${local.name_prefix}-worker-lambda"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "worker_lambda" {
  name = "${local.name_prefix}-worker-lambda"
  role = aws_iam_role.worker_lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat(
      [
        {
          Effect = "Allow"
          Action = [
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ]
          Resource = "${aws_cloudwatch_log_group.worker.arn}:*"
        },
        {
          Effect = "Allow"
          Action = [
            "s3:GetObject"
          ]
          Resource = "${aws_s3_bucket.source_videos.arn}/uploads/*"
        },
        {
          Effect = "Allow"
          Action = [
            "s3:PutObject",
            "s3:GetObject"
          ]
          Resource = "${aws_s3_bucket.artifacts.arn}/processed/*"
        },
        {
          Effect = "Allow"
          Action = [
            "dynamodb:GetItem",
            "dynamodb:UpdateItem"
          ]
          Resource = aws_dynamodb_table.jobs.arn
        },
        {
          Effect = "Allow"
          Action = [
            "sqs:ReceiveMessage",
            "sqs:DeleteMessage",
            "sqs:GetQueueAttributes",
            "sqs:ChangeMessageVisibility"
          ]
          Resource = aws_sqs_queue.processing.arn
        }
      ],
      var.model_secret_arn == "" ? [] : [
        {
          Effect   = "Allow"
          Action   = "secretsmanager:GetSecretValue"
          Resource = var.model_secret_arn
        }
      ]
    )
  })
}
