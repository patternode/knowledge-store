# The pipeline: one Fargate task that runs the idempotent sweep (knowledge-store run), and the
# triggers that start it.
#
#   upload to landing/ or a new ontology/active.json
#     -> S3 event -> EventBridge rule -> SQS queue
#     -> EventBridge Pipe -> ECS RunTask
#   EventBridge Scheduler (every schedule_expression) -> ECS RunTask   the safety net
#
# At the end of each sweep the task loads the gold RDF into Neptune (when neptune is set; the
# task reaches it inside the VPC) and writes the passages for the Knowledge Base (when
# knowledge_base is set), starting an ingestion job when any changed.
#
# Pipes allows a batch of only one message for an ECS target, so each upload starts a task.
# The task takes an S3 lock, so a task started while one runs exits at once, and the running
# one keeps sweeping until nothing new arrives. Because the sweep is idempotent, the schedule
# catches anything an event missed. A bulk upload therefore starts many short-lived tasks;
# upload large sets in few files, or lean on the schedule.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.66" }
  }
}

variable "name" { type = string }
variable "image_uri" { type = string }
variable "lake_bucket" { type = string }
variable "lake_bucket_arn" { type = string }
variable "extra_read_bucket_arns" {
  type        = list(string)
  default     = []
  description = "other buckets sources read from (an s3_landing source with its own bucket)"
}
variable "subnet_ids" { type = list(string) }
variable "vpc_id" { type = string }
variable "assign_public_ip" {
  type    = bool
  default = true
}
variable "llm_provider" {
  type    = string
  default = "bedrock"
}
variable "anthropic_api_key_secret_arn" {
  type    = string
  default = ""
}
variable "extraction_model_id" { type = string }
variable "cpu" {
  type    = number
  default = 1024
}
variable "memory" {
  type    = number
  default = 4096
}
variable "batching_window_s" {
  type        = number
  default     = 60
  description = "how long uploads are gathered before a run starts"
}
variable "schedule_expression" {
  type        = string
  default     = "rate(6 hours)"
  description = "the safety-net sweep; an EventBridge Scheduler expression"
}
variable "schedule_enabled" {
  type    = bool
  default = true
}
variable "log_retention_days" {
  type    = number
  default = 30
}
variable "neptune" {
  type = object({
    endpoint = string
    port     = number
    data_arn = string
  })
  default     = null
  description = "the knowledge graph the sweep loads the gold RDF into; null for none"
}
variable "knowledge_base" {
  type = object({
    id             = string
    arn            = string
    data_source_id = string
  })
  default     = null
  description = "the passages' vector index the sweep keeps in step; null for none"
}
variable "permissions_boundary" {
  type        = string
  default     = null
  description = "an IAM policy ARN set as the permissions boundary of every role this module creates; null for none"
}
variable "tags" {
  type    = map(string)
  default = {}
}

data "aws_region" "current" {}
data "aws_caller_identity" "me" {}

locals {
  anthropic = var.llm_provider == "anthropic" && var.anthropic_api_key_secret_arn != ""
}

resource "aws_ecs_cluster" "this" {
  name = var.name
  setting {
    name  = "containerInsights"
    value = "disabled"
  }
  tags = var.tags
}

resource "aws_cloudwatch_log_group" "pipeline" {
  name              = "/ecs/${var.name}-pipeline"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_security_group" "task" {
  name        = "${var.name}-pipeline"
  description = "knowledge-store pipeline tasks: egress only"
  vpc_id      = var.vpc_id
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = var.tags
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name                 = "${var.name}-pipeline-exec"
  permissions_boundary = var.permissions_boundary
  assume_role_policy   = data.aws_iam_policy_document.ecs_assume.json
  tags                 = var.tags
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name                 = "${var.name}-pipeline-task"
  permissions_boundary = var.permissions_boundary
  assume_role_policy   = data.aws_iam_policy_document.ecs_assume.json
  tags                 = var.tags
}

resource "aws_iam_role_policy" "task" {
  role = aws_iam_role.task.id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat([
    { Sid = "Lake", Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
    Resource = "${var.lake_bucket_arn}/*" },
    { Sid = "LakeList", Effect = "Allow", Action = ["s3:ListBucket"], Resource = var.lake_bucket_arn },
    { Sid = "Models", Effect = "Allow", Action = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      Resource = ["arn:aws:bedrock:*::foundation-model/*",
    "arn:aws:bedrock:*:${data.aws_caller_identity.me.account_id}:inference-profile/*"] },
    ], length(var.extra_read_bucket_arns) == 0 ? [] : [
    { Sid = "SourceBuckets", Effect = "Allow", Action = ["s3:GetObject", "s3:ListBucket"],
    Resource = concat(var.extra_read_bucket_arns, [for b in var.extra_read_bucket_arns : "${b}/*"]) },
    ], local.anthropic ? [
    { Sid = "AnthropicKey", Effect = "Allow", Action = "secretsmanager:GetSecretValue",
    Resource = var.anthropic_api_key_secret_arn },
    ] : [], var.neptune != null ? [
    { Sid    = "LoadGraph", Effect = "Allow",
      Action = ["neptune-db:connect", "neptune-db:ReadDataViaQuery", "neptune-db:WriteDataViaQuery", "neptune-db:DeleteDataViaQuery"],
    Resource = var.neptune.data_arn },
    ] : [], var.knowledge_base != null ? [
    { Sid = "SyncPassages", Effect = "Allow", Action = ["bedrock:StartIngestionJob", "bedrock:GetIngestionJob"],
    Resource = var.knowledge_base.arn },
  ] : []) })
}

resource "aws_ecs_task_definition" "pipeline" {
  family                   = "${var.name}-pipeline"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform {
    cpu_architecture        = "X86_64"
    operating_system_family = "LINUX"
  }
  ephemeral_storage { size_in_gib = 30 }
  container_definitions = jsonencode([{
    name      = "pipeline"
    image     = var.image_uri
    essential = true
    command   = ["run"]
    environment = concat([
      { name = "LAKE_URI", value = "s3://${var.lake_bucket}" },
      { name = "LLM_PROVIDER", value = var.llm_provider },
      { name = "EXTRACTION_MODEL_ID", value = var.extraction_model_id },
      { name = "AWS_REGION", value = data.aws_region.current.region },
      ], local.anthropic ? [{ name = "ANTHROPIC_API_KEY_SECRET", value = var.anthropic_api_key_secret_arn }] : [],
      var.neptune != null ? [{ name = "NEPTUNE_ENDPOINT", value = var.neptune.endpoint },
      { name = "NEPTUNE_PORT", value = tostring(var.neptune.port) }] : [],
      var.knowledge_base != null ? [{ name = "KNOWLEDGE_BASE_ID", value = var.knowledge_base.id },
    { name = "KNOWLEDGE_BASE_DATA_SOURCE_ID", value = var.knowledge_base.data_source_id }] : [])
    logConfiguration = {
      logDriver = "awslogs"
      options = { "awslogs-group" = aws_cloudwatch_log_group.pipeline.name,
      "awslogs-region" = data.aws_region.current.region, "awslogs-stream-prefix" = "run" }
    }
  }])
  tags = var.tags
}

# --- event trigger ------------------------------------------------------------------------

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name}-uploads-dlq"
  message_retention_seconds = 1209600
  tags                      = var.tags
}

resource "aws_sqs_queue" "uploads" {
  name                       = "${var.name}-uploads"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 86400
  redrive_policy             = jsonencode({ deadLetterTargetArn = aws_sqs_queue.dlq.arn, maxReceiveCount = 5 })
  tags                       = var.tags
}

resource "aws_cloudwatch_event_rule" "uploads" {
  name        = "${var.name}-uploads"
  description = "content landed, or a new ontology version was activated"
  event_pattern = jsonencode({
    source        = ["aws.s3"]
    "detail-type" = ["Object Created"]
    detail = {
      bucket = { name = [var.lake_bucket] }
      object = { key = [{ prefix = "landing/" }, { suffix = "/ontology/active.json" }] }
    }
  })
  tags = var.tags
}

resource "aws_cloudwatch_event_target" "uploads" {
  rule = aws_cloudwatch_event_rule.uploads.name
  arn  = aws_sqs_queue.uploads.arn
}

resource "aws_sqs_queue_policy" "uploads" {
  queue_url = aws_sqs_queue.uploads.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect    = "Allow", Principal = { Service = "events.amazonaws.com" }, Action = "sqs:SendMessage",
    Resource  = aws_sqs_queue.uploads.arn,
    Condition = { ArnEquals = { "aws:SourceArn" = aws_cloudwatch_event_rule.uploads.arn } }
  }] })
}

data "aws_iam_policy_document" "run_task" {
  statement {
    actions   = ["ecs:RunTask"]
    resources = ["${aws_ecs_task_definition.pipeline.arn_without_revision}:*"]
  }
  statement {
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.execution.arn, aws_iam_role.task.arn]
  }
}

resource "aws_iam_role" "pipe" {
  name                 = "${var.name}-pipe"
  permissions_boundary = var.permissions_boundary
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect    = "Allow", Principal = { Service = "pipes.amazonaws.com" }, Action = "sts:AssumeRole",
    Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.me.account_id } }
  }] })
  tags = var.tags
}

resource "aws_iam_role_policy" "pipe" {
  role = aws_iam_role.pipe.id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat(
    jsondecode(data.aws_iam_policy_document.run_task.json).Statement,
    [{ Effect = "Allow", Action = ["sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"],
    Resource = aws_sqs_queue.uploads.arn }]
  ) })
}

resource "aws_pipes_pipe" "uploads" {
  name     = "${var.name}-uploads"
  role_arn = aws_iam_role.pipe.arn
  source   = aws_sqs_queue.uploads.arn
  target   = aws_ecs_cluster.this.arn
  source_parameters {
    sqs_queue_parameters {
      batch_size                         = 1 # the most Pipes allows for an ECS target
      maximum_batching_window_in_seconds = var.batching_window_s
    }
  }
  target_parameters {
    ecs_task_parameters {
      task_definition_arn = aws_ecs_task_definition.pipeline.arn_without_revision
      launch_type         = "FARGATE"
      task_count          = 1
      network_configuration {
        aws_vpc_configuration {
          subnets          = var.subnet_ids
          security_groups  = [aws_security_group.task.id]
          assign_public_ip = var.assign_public_ip ? "ENABLED" : "DISABLED"
        }
      }
    }
  }
  depends_on = [aws_iam_role_policy.pipe]
  tags       = var.tags
}

# --- schedule -----------------------------------------------------------------------------

resource "aws_iam_role" "scheduler" {
  name                 = "${var.name}-scheduler"
  permissions_boundary = var.permissions_boundary
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect    = "Allow", Principal = { Service = "scheduler.amazonaws.com" }, Action = "sts:AssumeRole",
    Condition = { StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.me.account_id } }
  }] })
  tags = var.tags
}

resource "aws_iam_role_policy" "scheduler" {
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.run_task.json
}

resource "aws_scheduler_schedule" "sweep" {
  name                = "${var.name}-sweep"
  schedule_expression = var.schedule_expression
  state               = var.schedule_enabled ? "ENABLED" : "DISABLED"
  flexible_time_window { mode = "OFF" }
  target {
    arn      = aws_ecs_cluster.this.arn
    role_arn = aws_iam_role.scheduler.arn
    ecs_parameters {
      task_definition_arn = aws_ecs_task_definition.pipeline.arn_without_revision
      launch_type         = "FARGATE"
      task_count          = 1
      network_configuration {
        subnets          = var.subnet_ids
        security_groups  = [aws_security_group.task.id]
        assign_public_ip = var.assign_public_ip
      }
    }
  }
}

output "cluster_name" { value = aws_ecs_cluster.this.name }
output "cluster_arn" { value = aws_ecs_cluster.this.arn }
output "task_definition" { value = aws_ecs_task_definition.pipeline.family }
output "security_group_id" { value = aws_security_group.task.id }
output "log_group" { value = aws_cloudwatch_log_group.pipeline.name }
output "task_role_arn" { value = aws_iam_role.task.arn }
