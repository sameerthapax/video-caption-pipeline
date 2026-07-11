# AWS Infrastructure

This directory defines a free-tier-friendly development deployment for the video caption pipeline in `us-east-1` by default. It does not create a VPC, NAT Gateway, RDS, ECS service, ALB, OpenSearch, WAF, or provisioned DynamoDB capacity.

## Architecture

- `web` is hosted on AWS Amplify Hosting from GitHub `main`.
- Source videos upload to a private S3 bucket using API-generated presigned PUT URLs.
- Processing artifacts and final results are stored in a second private S3 bucket.
- Job state lives in DynamoDB with `job_id` as the partition key and on-demand billing.
- API Gateway HTTP API invokes a small Python Lambda for upload/job/result routes.
- The API enqueues SQS messages after an uploaded object is registered.
- The worker runs as a Lambda container image from ECR and processes SQS messages with batch size `1`.
- External model credentials are referenced through Secrets Manager or secure Lambda environment variables, not committed files.

## Prerequisites

- Terraform `>= 1.8`.
- AWS CLI credentials for local planning/apply or GitHub OIDC for Actions.
- Docker for building the worker image.
- An Amplify GitHub authorization. Prefer the Amplify GitHub App. If `github_access_token` is used, remember Terraform state can contain sensitive values.

## Local Deployment

```sh
cp infra/aws/terraform.tfvars.example infra/aws/terraform.tfvars
npm run aws-tf-init
npm run aws-tf-plan
```

Do not commit `terraform.tfvars`, plans, local state, or secrets.

Apply only when ready:

```sh
npm run aws-tf-apply
```

## GitHub OIDC Setup

Bootstrap creates an encrypted S3 state bucket and a GitHub Actions deployment role:

```sh
cd infra/aws/bootstrap
terraform init
terraform apply \
  -var='github_owner=sameerthapax' \
  -var='github_repository=video-caption-pipeline' \
  -var='github_environment=development'
```

Store the `github_actions_role_arn` output as GitHub Environment variable `AWS_ROLE_ARN` in the `development` environment. Also set `AWS_REGION=us-east-1`.

The bootstrap trust policy restricts OIDC to:

```text
repo:sameerthapax/video-caption-pipeline:environment:development
```

The bootstrap role is broad enough to create the initial resources but does not attach `AdministratorAccess`. After the first deployment, replace it with a tighter policy scoped to the exact created ARNs from Terraform outputs/state.

## GitHub Actions Variables

Set these in the `development` GitHub Environment:

- `AWS_ROLE_ARN`: output from `infra/aws/bootstrap`.
- `AWS_REGION`: normally `us-east-1`.
- `TF_STATE_BUCKET`: bootstrap output `state_bucket`.
- `TF_STATE_LOCK_TABLE`: bootstrap output `state_lock_table`.
- `TF_STATE_KEY`: optional override for the Terraform state object key. Default is `video-caption-pipeline/dev/terraform.tfstate`.
- `WORKER_ECR_REPOSITORY_URL`: output `worker_ecr_repository_url`.
- `WORKER_LAMBDA_NAME`: output `worker_lambda_name` after the worker Lambda exists.

Do not store long-lived AWS access keys in GitHub.

## Amplify GitHub Authorization

The Terraform app points Amplify at `https://github.com/${github_owner}/${github_repository}` and configures automatic builds for `main`. The build spec uses the inspected Nx project:

- project name: `web`
- app root: `apps/web`
- output: `dist/apps/web`

Authorize repository access in the Amplify console using the GitHub App, or provide `github_access_token` only as a sensitive local variable with the state-risk caveat.
For GitHub Actions, set it as the `development` environment secret `TF_VAR_github_access_token`.

## Worker Image Bootstrap

1. Apply Terraform once with `worker_image_uri = ""` to create ECR and the rest of the stack.
2. Set GitHub variable `WORKER_ECR_REPOSITORY_URL` from Terraform output.
3. Run the `Worker Image` workflow or build/push locally using the commit SHA as the tag.
4. Set `worker_image_uri` in Terraform to the immutable ECR image URI.
5. Apply Terraform again to create the worker Lambda and SQS event source mapping.
6. Set GitHub variable `WORKER_LAMBDA_NAME` from Terraform output so later image workflows can update the function code.

## Secrets

Prefer creating a Secrets Manager secret outside Terraform, for example:

```json
{
  "FIREWORKS_API_KEY": "example",
  "GOOGLE_GEMINI_API_KEY": "example",
  "OPENAI_API_KEY": "example"
}
```

Then set only `model_secret_arn`. Terraform state can still contain sensitive variable values and ARNs, so never put secret values in committed tfvars or workflow files.

## Remote State Migration

The main config starts with local state. After bootstrap:

```sh
terraform -chdir=infra/aws init \
  -backend-config=backend.hcl \
  -migrate-state
```

Fill `backend.hcl` from `backend.hcl.example` using the bootstrap `state_bucket` and `state_lock_table` outputs.
GitHub Actions uses the same backend by generating `backend.ci.hcl` from `TF_STATE_BUCKET`, `TF_STATE_LOCK_TABLE`, and optional `TF_STATE_KEY`.

## Testing

Local checks that do not create cloud resources:

```sh
terraform -chdir=infra/aws fmt -recursive
terraform -chdir=infra/aws init
terraform -chdir=infra/aws validate
npm run test:web
npm run test:api
```

For worker validation, build the image:

```sh
npm run aws-worker-build
```

## Teardown

Empty S3 buckets and ECR images before destroy if AWS reports non-empty resources:

```sh
npm run aws-tf-destroy
```

## Cost Warnings

- Keep `worker_reserved_concurrency` low in development, or leave it unset if your AWS account has a very small concurrency quota.
- The default log retention is 7 days.
- DynamoDB uses on-demand billing.
- The optional budget is enabled only when `budget_email` is set.
- Lambda duration can still become expensive if model calls or FFmpeg processing hang.

## Known Lambda Constraints

- Worker timeout defaults to 900 seconds, which is Lambda's maximum.
- `/tmp` storage defaults to 4096 MB and is configurable up to 10240 MB.
- No GPU is available or required.
- FFmpeg is bundled in the Lambda container image.
- Very large videos or provider latency can exceed Lambda limits; this setup is intended for short videos under 3 minutes.
