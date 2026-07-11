resource "aws_amplify_app" "frontend" {
  name       = "${local.name_prefix}-frontend"
  repository = "https://github.com/${var.github_owner}/${var.github_repository}"

  access_token = var.github_access_token

  environment_variables = {
    VITE_API_BASE_URL = aws_apigatewayv2_stage.default.invoke_url
  }

  build_spec = <<-EOT
    version: 1
    frontend:
      phases:
        preBuild:
          commands:
            - npm ci
        build:
          commands:
            - npx nx build ${local.frontend_project_name}
      artifacts:
        baseDirectory: ${local.frontend_output_dir}
        files:
          - '**/*'
      cache:
        paths:
          - node_modules/**/*
          - .nx/cache/**/*
  EOT

  lifecycle {
    ignore_changes = [access_token]
  }
}

resource "aws_amplify_branch" "main" {
  app_id            = aws_amplify_app.frontend.id
  branch_name       = var.github_branch
  enable_auto_build = true
  framework         = "React"
  stage             = "DEVELOPMENT"
}
