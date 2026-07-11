locals {
  name_prefix = "${var.project_name}-${var.environment}"

  frontend_project_name = "web"
  frontend_app_root     = "apps/web"
  frontend_output_dir   = "dist/apps/web"

  api_lambda_name    = "${local.name_prefix}-api"
  worker_lambda_name = "${local.name_prefix}-worker"

  tags = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
}
