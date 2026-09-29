# The pipeline's container image, built inside the deploying account.
#
#   terraform zips the source (the repository root) -> s3://<artifacts>/source/<hash>.zip
#   the upload raises an S3 event -> EventBridge -> CodeBuild StartBuild
#   CodeBuild builds the Dockerfile and pushes <repo>:latest and <repo>:<hash> to ECR
#
# Nothing runs on the machine that applies Terraform (no docker, no local-exec), and nothing
# is pulled from a registry the deployer does not own except the Python base image from ECR
# Public. Each source change is a new bundle key, so it rebuilds; an unchanged source does not.
# The first build takes a few minutes after the first apply; the pipeline's task definition
# uses :latest, so tasks started after the build pick it up.

terraform {
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 6.66" }
    archive = { source = "hashicorp/archive", version = "~> 2.7" }
  }
}

variable "name" { type = string }
variable "source_dir" {
  type        = string
  description = "the Knowledge Store source directory (holds Dockerfile, pyproject.toml, src/)"
}
variable "build_agent" {
  type        = bool
  default     = false
  description = "also build the example agent image (linux/arm64, Dockerfile.agent) for AgentCore Runtime"
}
variable "tags" {
  type    = map(string)
  default = {}
}

data "aws_caller_identity" "me" {}
data "aws_region" "current" {}

resource "aws_ecr_repository" "pipeline" {
  name                 = "${var.name}-pipeline"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  image_scanning_configuration { scan_on_push = true }
  tags = var.tags
}

resource "aws_ecr_lifecycle_policy" "pipeline" {
  repository = aws_ecr_repository.pipeline.name
  policy = jsonencode({ rules = [{
    rulePriority = 1, description = "keep the last 10 images"
    selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 10 }
    action       = { type = "expire" }
  }] })
}

resource "aws_s3_bucket" "artifacts" {
  bucket        = "${var.name}-build-${data.aws_caller_identity.me.account_id}"
  force_destroy = true
  tags          = var.tags
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_notification" "artifacts" {
  bucket      = aws_s3_bucket.artifacts.id
  eventbridge = true
}

data "archive_file" "source" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.root}/.build/${var.name}-source.zip"
  # Only what the image needs: Dockerfile, pyproject.toml, README, LICENSE and src/.
  excludes = concat(flatten([for d in ["infra", "portal", "tests", "examples", "docs", "build", ".git", ".pytest_cache",
  "src/knowledge_store.egg-info"] : [d, "${d}/**"]]), ["**/__pycache__/**"])
}

resource "aws_s3_object" "source" {
  bucket = aws_s3_bucket.artifacts.id
  key    = "source/${data.archive_file.source.output_sha256}.zip"
  source = data.archive_file.source.output_path
  # The upload starts the builds, so everything StartBuild needs must exist first, including the
  # trigger role's policy: without it the first builds fail and nothing retries them.
  depends_on = [aws_s3_bucket_notification.artifacts, aws_cloudwatch_event_target.build,
  aws_cloudwatch_event_target.agent_build, aws_iam_role_policy.events]
}

resource "aws_iam_role" "codebuild" {
  name = "${var.name}-codebuild"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
  Effect = "Allow", Principal = { Service = "codebuild.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags = var.tags
}

resource "aws_iam_role_policy" "codebuild" {
  role = aws_iam_role.codebuild.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], Resource = "*" },
    { Effect = "Allow", Action = ["s3:GetObject", "s3:GetObjectVersion"], Resource = "${aws_s3_bucket.artifacts.arn}/source/*" },
    { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
    { Effect = "Allow", Action = ["ecr:BatchCheckLayerAvailability", "ecr:CompleteLayerUpload", "ecr:InitiateLayerUpload",
      "ecr:PutImage", "ecr:UploadLayerPart", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
    Resource = concat([aws_ecr_repository.pipeline.arn], aws_ecr_repository.agent[*].arn) },
  ] })
}

resource "aws_codebuild_project" "image" {
  name          = "${var.name}-image"
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = 30
  artifacts { type = "NO_ARTIFACTS" }
  environment {
    compute_type    = "BUILD_GENERAL1_SMALL"
    image           = "aws/codebuild/amazonlinux-x86_64-standard:5.0"
    type            = "LINUX_CONTAINER"
    privileged_mode = true
    environment_variable {
      name  = "REPO"
      value = aws_ecr_repository.pipeline.repository_url
    }
  }
  source {
    type      = "S3"
    location  = "${aws_s3_bucket.artifacts.id}/source/placeholder.zip"
    buildspec = <<-YAML
      version: 0.2
      phases:
        pre_build:
          commands:
            - aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $${REPO%%/*}
            - TAG=$(basename "$CODEBUILD_SOURCE_VERSION" .zip | cut -c1-12)
        build:
          commands:
            - docker build -t $REPO:latest -t $REPO:$TAG .
        post_build:
          commands:
            - docker push $REPO:$TAG
            - docker push $REPO:latest
    YAML
  }
  logs_config {
    cloudwatch_logs { group_name = "/codebuild/${var.name}-image" }
  }
  tags = var.tags
}

resource "aws_cloudwatch_event_rule" "source_uploaded" {
  name = "${var.name}-source-uploaded"
  event_pattern = jsonencode({
    source        = ["aws.s3"]
    "detail-type" = ["Object Created"]
    detail        = { bucket = { name = [aws_s3_bucket.artifacts.id] }, object = { key = [{ prefix = "source/" }] } }
  })
  tags = var.tags
}

resource "aws_iam_role" "events" {
  name = "${var.name}-build-trigger"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
  Effect = "Allow", Principal = { Service = "events.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags = var.tags
}

resource "aws_iam_role_policy" "events" {
  role = aws_iam_role.events.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
  { Effect = "Allow", Action = "codebuild:StartBuild", Resource = concat([aws_codebuild_project.image.arn], aws_codebuild_project.agent[*].arn) }] })
}

# The build runs against the uploaded bundle: sourceLocationOverride names it.
resource "aws_cloudwatch_event_target" "build" {
  rule     = aws_cloudwatch_event_rule.source_uploaded.name
  arn      = aws_codebuild_project.image.arn
  role_arn = aws_iam_role.events.arn
  input_transformer {
    input_paths    = { bucket = "$.detail.bucket.name", key = "$.detail.object.key" }
    input_template = "{\"sourceLocationOverride\": \"<bucket>/<key>\"}"
  }
}

output "repository_url" { value = aws_ecr_repository.pipeline.repository_url }
output "repository_arn" { value = aws_ecr_repository.pipeline.arn }
output "image_uri" { value = "${aws_ecr_repository.pipeline.repository_url}:latest" }
output "source_key" { value = aws_s3_object.source.key }
output "codebuild_project" { value = aws_codebuild_project.image.name }

# --- the example agent's image: arm64, which AgentCore Runtime requires ----------------------

resource "aws_ecr_repository" "agent" {
  count                = var.build_agent ? 1 : 0
  name                 = "${var.name}-agent"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  image_scanning_configuration { scan_on_push = true }
  tags = var.tags
}

resource "aws_ecr_lifecycle_policy" "agent" {
  count      = var.build_agent ? 1 : 0
  repository = aws_ecr_repository.agent[0].name
  policy = jsonencode({ rules = [{
    rulePriority = 1, description = "keep the last 10 images"
    selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 10 }
    action       = { type = "expire" }
  }] })
}

resource "aws_codebuild_project" "agent" {
  count         = var.build_agent ? 1 : 0
  name          = "${var.name}-agent-image"
  service_role  = aws_iam_role.codebuild.arn
  build_timeout = 30
  artifacts { type = "NO_ARTIFACTS" }
  environment {
    compute_type    = "BUILD_GENERAL1_SMALL"
    image           = "aws/codebuild/amazonlinux-aarch64-standard:3.0"
    type            = "ARM_CONTAINER"
    privileged_mode = true
    environment_variable {
      name  = "REPO"
      value = aws_ecr_repository.agent[0].repository_url
    }
  }
  source {
    type      = "S3"
    location  = "${aws_s3_bucket.artifacts.id}/source/placeholder.zip"
    buildspec = <<-YAML
      version: 0.2
      phases:
        pre_build:
          commands:
            - aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $${REPO%%/*}
            - TAG=$(basename "$CODEBUILD_SOURCE_VERSION" .zip | cut -c1-12)
        build:
          commands:
            - docker build -f Dockerfile.agent -t $REPO:latest -t $REPO:$TAG .
        post_build:
          commands:
            - docker push $REPO:$TAG
            - docker push $REPO:latest
    YAML
  }
  logs_config {
    cloudwatch_logs { group_name = "/codebuild/${var.name}-agent-image" }
  }
  tags = var.tags
}

resource "aws_cloudwatch_event_target" "agent_build" {
  count    = var.build_agent ? 1 : 0
  rule     = aws_cloudwatch_event_rule.source_uploaded.name
  arn      = aws_codebuild_project.agent[0].arn
  role_arn = aws_iam_role.events.arn
  input_transformer {
    input_paths    = { bucket = "$.detail.bucket.name", key = "$.detail.object.key" }
    input_template = "{\"sourceLocationOverride\": \"<bucket>/<key>\"}"
  }
}

output "agent_repository_url" { value = try(aws_ecr_repository.agent[0].repository_url, "") }
output "agent_repository_arn" { value = try(aws_ecr_repository.agent[0].arn, "") }
output "agent_image_uri" { value = try("${aws_ecr_repository.agent[0].repository_url}:latest", "") }
output "agent_codebuild_project" { value = try(aws_codebuild_project.agent[0].name, "") }
