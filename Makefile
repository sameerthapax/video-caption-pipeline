AWS_TF_DIR := infra/aws
AWS_WORKER_IMAGE ?= video-caption-pipeline-worker:local

.PHONY: aws-tf-init aws-tf-plan aws-tf-apply aws-tf-destroy aws-worker-build

aws-tf-init:
	terraform -chdir=$(AWS_TF_DIR) init

aws-tf-plan:
	terraform -chdir=$(AWS_TF_DIR) plan

aws-tf-apply:
	terraform -chdir=$(AWS_TF_DIR) apply

aws-tf-destroy:
	terraform -chdir=$(AWS_TF_DIR) destroy

aws-worker-build:
	docker build -f apps/worker/Dockerfile.lambda -t $(AWS_WORKER_IMAGE) .
