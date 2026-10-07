# The chat agent and what it needs, each for one job:
#
#   Gateway        the knowledge tools over MCP, authenticated with the caller's Cognito token,
#     interceptor  a REQUEST Lambda that writes the caller's scope into every tool call
#     graph        target: the graph tools Lambda, in the VPC beside Neptune (read-only access)
#     passages     target: the passage tools Lambda, outside the VPC, searching the Knowledge Base
#   Guardrail      screens each question, and checks each claim of an answer against the passages
#                  it cites (contextual grounding); applied by the agent with ApplyGuardrail
#   Runtime        the agent container (Dockerfile.agent); a prod endpoint pins a version
#
# The agent acts only as its caller: the Runtime accepts the caller's Cognito access token and the
# agent presents the same token to the Gateway, so it can never read more than the person asking.
#
# Two applies: the Runtime needs its image, which CodeBuild builds after the first apply. Set
# runtime_enabled = true once the agent image exists in ECR. Until then the chat API answers with
# the portal's own tool loop.

terraform {
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 6.66" }
    archive = { source = "hashicorp/archive", version = "~> 2.7" }
  }
}

variable "name" { type = string }
variable "package_root" {
  type        = string
  description = "the src directory holding the knowledge-store package, zipped for the tool and interceptor Lambdas"
}
variable "tool_schema_dir" {
  type        = string
  description = "src/knowledge_store/tools: schema-graph.json and schema-passages.json, kept in step with the code by a test"
}
variable "lake_bucket" { type = string }
variable "lake_bucket_arn" { type = string }
variable "discovery_url" { type = string }
variable "allowed_client_ids" {
  type        = list(string)
  description = "Cognito app clients whose access tokens the Runtime and Gateway accept"
}
variable "private_group" {
  type    = string
  default = "private-readers"
}
variable "scope_prefix" { type = string }
variable "agent_image_uri" {
  type    = string
  default = ""
}
variable "runtime_enabled" {
  type    = bool
  default = false
}
variable "prod_version" {
  type        = string
  default     = ""
  description = "a Runtime version to pin as the prod endpoint; empty for none (DEFAULT always follows the latest)"
}
variable "agent_model_id" { type = string }
variable "neptune" {
  type = object({
    endpoint                 = string
    port                     = number
    data_arn                 = string
    client_security_group_id = string
    private_subnet_ids       = list(string)
  })
  default     = null
  description = "the knowledge graph; null answers the graph tools from the lake's projection instead"
}
variable "knowledge_base" {
  type = object({
    id  = string
    arn = string
  })
  default     = null
  description = "the passages' vector index; null searches passages by keyword instead"
}
variable "guardrail" {
  type = object({
    enabled             = optional(bool, true)
    grounding_threshold = optional(number, 0.75)
  })
  default = {}
}
variable "valves" {
  type = object({
    max_tool_calls    = optional(number, 16)
    max_model_calls   = optional(number, 14)
    max_output_tokens = optional(number, 4000)
    grounding_repairs = optional(number, 1)
  })
  default = {}
}
variable "log_retention_days" {
  type    = number
  default = 30
}
variable "tags" {
  type    = map(string)
  default = {}
}

data "aws_region" "current" {}
data "aws_caller_identity" "me" {}

locals {
  region   = data.aws_region.current.region
  account  = data.aws_caller_identity.me.account_id
  ident    = replace(var.name, "-", "_")
  runtime  = var.runtime_enabled && var.agent_image_uri != ""
  in_graph = var.neptune != null
  # what each toolset reads in the lake (per collection, under collections/<id>/)
  graph_layers    = ["gold", "ontology", "config"]
  passages_layers = ["gold", "silver", "config"]
  targets = {
    graph    = { schema = "${var.tool_schema_dir}/schema-graph.json", lambda = aws_lambda_function.graph.arn }
    passages = { schema = "${var.tool_schema_dir}/schema-passages.json", lambda = aws_lambda_function.passages.arn }
  }
}

data "aws_iam_policy_document" "agentcore_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account]
    }
  }
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# --- the tool and interceptor Lambdas (one zip, stdlib and boto3 only) ------------------------

data "archive_file" "code" {
  type        = "zip"
  source_dir  = var.package_root
  output_path = "${path.root}/.build/${var.name}-agent-tools.zip"
  excludes    = ["knowledge_store.egg-info", "knowledge_store.egg-info/**", "**/__pycache__/**", "**/*.pyc"]
}

resource "aws_iam_role" "graph" {
  name               = "${var.name}-tools-graph"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "graph_logs" {
  role       = aws_iam_role.graph.name
  policy_arn = local.in_graph ? "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole" : "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "graph" {
  role = aws_iam_role.graph.id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat([
    { Sid = "ReadServedLayers", Effect = "Allow", Action = "s3:GetObject",
    Resource = concat(["${var.lake_bucket_arn}/config/*"], [for p in local.graph_layers : "${var.lake_bucket_arn}/collections/*/${p}/*"]) },
    { Sid = "ListServedLayers", Effect = "Allow", Action = "s3:ListBucket", Resource = var.lake_bucket_arn,
    Condition = { StringLike = { "s3:prefix" = concat(["config/*"], [for p in local.graph_layers : "collections/*/${p}/*"]) } } },
    ], local.in_graph ? [
    # read only: no tool call can change the graph, whatever query it sends
    { Sid = "ReadGraph", Effect = "Allow", Action = ["neptune-db:connect", "neptune-db:ReadDataViaQuery"], Resource = var.neptune.data_arn },
  ] : []) })
}

resource "aws_lambda_function" "graph" {
  function_name    = "${var.name}-tools-graph"
  role             = aws_iam_role.graph.arn
  runtime          = "python3.12"
  handler          = "knowledge_store.tools.gateway.lambda_handler"
  filename         = data.archive_file.code.output_path
  source_code_hash = data.archive_file.code.output_base64sha256
  timeout          = 60
  memory_size      = 1024
  environment {
    variables = merge({ LAKE_BUCKET = var.lake_bucket, TOOLSET = "graph" },
    local.in_graph ? { NEPTUNE_ENDPOINT = var.neptune.endpoint, NEPTUNE_PORT = tostring(var.neptune.port) } : {})
  }
  dynamic "vpc_config" {
    for_each = local.in_graph ? [1] : []
    content {
      subnet_ids         = var.neptune.private_subnet_ids
      security_group_ids = [var.neptune.client_security_group_id]
    }
  }
  depends_on = [aws_iam_role_policy_attachment.graph_logs]
  tags       = var.tags
}

resource "aws_iam_role" "passages" {
  name               = "${var.name}-tools-passages"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "passages_logs" {
  role       = aws_iam_role.passages.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "passages" {
  role = aws_iam_role.passages.id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat([
    { Sid = "ReadServedLayers", Effect = "Allow", Action = "s3:GetObject",
    Resource = concat(["${var.lake_bucket_arn}/config/*"], [for p in local.passages_layers : "${var.lake_bucket_arn}/collections/*/${p}/*"]) },
    { Sid = "ListServedLayers", Effect = "Allow", Action = "s3:ListBucket", Resource = var.lake_bucket_arn,
    Condition = { StringLike = { "s3:prefix" = concat(["config/*"], [for p in local.passages_layers : "collections/*/${p}/*"]) } } },
    ], var.knowledge_base != null ? [
    { Sid = "SearchPassages", Effect = "Allow", Action = "bedrock:Retrieve", Resource = var.knowledge_base.arn },
  ] : []) })
}

resource "aws_lambda_function" "passages" {
  function_name    = "${var.name}-tools-passages"
  role             = aws_iam_role.passages.arn
  runtime          = "python3.12"
  handler          = "knowledge_store.tools.gateway.lambda_handler"
  filename         = data.archive_file.code.output_path
  source_code_hash = data.archive_file.code.output_base64sha256
  timeout          = 60
  memory_size      = 1024
  environment {
    variables = merge({ LAKE_BUCKET = var.lake_bucket, TOOLSET = "passages" },
    var.knowledge_base != null ? { KNOWLEDGE_BASE_ID = var.knowledge_base.id } : {})
  }
  tags = var.tags
}

resource "aws_iam_role" "interceptor" {
  name               = "${var.name}-agent-interceptor"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "interceptor_logs" {
  role       = aws_iam_role.interceptor.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "interceptor" {
  function_name    = "${var.name}-agent-interceptor"
  role             = aws_iam_role.interceptor.arn
  runtime          = "python3.12"
  handler          = "knowledge_store.tools.interceptor.lambda_handler"
  filename         = data.archive_file.code.output_path
  source_code_hash = data.archive_file.code.output_base64sha256
  timeout          = 10
  memory_size      = 256
  environment { variables = { PRIVATE_GROUP = var.private_group, SCOPE_PREFIX = var.scope_prefix } }
  tags = var.tags
}

resource "aws_cloudwatch_log_group" "lambdas" {
  for_each          = toset(["${var.name}-tools-graph", "${var.name}-tools-passages"])
  name              = "/aws/lambda/${each.key}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# --- Gateway and its two targets ----------------------------------------------------------------

resource "aws_s3_object" "tool_schema" {
  for_each     = local.targets
  bucket       = var.lake_bucket
  key          = "agentcore/tool-schemas/${each.key}.json"
  source       = each.value.schema
  etag         = filemd5(each.value.schema)
  content_type = "application/json"
}

resource "aws_iam_role" "gateway" {
  name               = "${var.name}-gateway"
  assume_role_policy = data.aws_iam_policy_document.agentcore_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "gateway" {
  role = aws_iam_role.gateway.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Sid = "Targets", Effect = "Allow", Action = "lambda:InvokeFunction",
    Resource = [aws_lambda_function.graph.arn, aws_lambda_function.passages.arn, aws_lambda_function.interceptor.arn] },
    { Sid = "ToolSchemas", Effect = "Allow", Action = "s3:GetObject", Resource = "${var.lake_bucket_arn}/agentcore/tool-schemas/*" },
  ] })
}

resource "aws_bedrockagentcore_gateway" "this" {
  name            = "${var.name}-tools"
  description     = "The knowledge graph and its passages as read-only tools, scoped by the caller's token"
  role_arn        = aws_iam_role.gateway.arn
  authorizer_type = "CUSTOM_JWT"
  authorizer_configuration {
    custom_jwt_authorizer {
      discovery_url   = var.discovery_url
      allowed_clients = var.allowed_client_ids
    }
  }
  protocol_type = "MCP"
  protocol_configuration {
    mcp {
      instructions = "Read-only tools over ontology-typed knowledge graphs, one per collection, and their source passages. Read the ontology first; cite passage ids with verbatim quotes."
    }
  }
  interceptor_configuration {
    interception_points = ["REQUEST"]
    interceptor {
      lambda { arn = aws_lambda_function.interceptor.arn }
    }
    input_configuration { pass_request_headers = true }
  }
  depends_on = [aws_iam_role_policy.gateway]
  tags       = var.tags
}

resource "aws_bedrockagentcore_gateway_target" "this" {
  for_each           = local.targets
  name               = each.key
  gateway_identifier = aws_bedrockagentcore_gateway.this.gateway_id
  description        = "knowledge-store ${each.key} tools"
  credential_provider_configuration {
    gateway_iam_role {}
  }
  target_configuration {
    mcp {
      lambda {
        lambda_arn = each.value.lambda
        tool_schema {
          s3 {
            uri                     = "s3://${var.lake_bucket}/${aws_s3_object.tool_schema[each.key].key}"
            bucket_owner_account_id = local.account
          }
        }
      }
    }
  }
  depends_on = [aws_iam_role_policy.gateway]
}

# --- Guardrail ----------------------------------------------------------------------------------

resource "aws_bedrock_guardrail" "this" {
  count                     = var.guardrail.enabled ? 1 : 0
  name                      = "${var.name}-chat"
  description               = "Screens questions, and checks each claim of an answer against the passages it cites"
  blocked_input_messaging   = "That question can't be answered here. Ask about the documents in this collection."
  blocked_outputs_messaging = "That answer could not be checked against the sources, so it is not shown."
  content_policy_config {
    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE"
    }
    dynamic "filters_config" {
      for_each = ["HATE", "INSULTS", "SEXUAL", "VIOLENCE", "MISCONDUCT"]
      content {
        type            = filters_config.value
        input_strength  = "MEDIUM"
        output_strength = "MEDIUM"
      }
    }
  }
  contextual_grounding_policy_config {
    filters_config {
      type      = "GROUNDING"
      threshold = var.guardrail.grounding_threshold
    }
  }
  tags = var.tags
}

resource "aws_bedrock_guardrail_version" "this" {
  count         = var.guardrail.enabled ? 1 : 0
  guardrail_arn = aws_bedrock_guardrail.this[0].guardrail_arn
  description   = "the version the agent applies"
}

# --- Runtime ------------------------------------------------------------------------------------

resource "aws_iam_role" "runtime" {
  name               = "${var.name}-agent-runtime"
  assume_role_policy = data.aws_iam_policy_document.agentcore_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "runtime" {
  role = aws_iam_role.runtime.id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat([
    { Sid = "Image", Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
    { Sid = "ImageLayers", Effect = "Allow", Action = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
    Resource = "arn:aws:ecr:${local.region}:${local.account}:repository/${var.name}-agent" },
    { Sid = "Models", Effect = "Allow", Action = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
    Resource = ["arn:aws:bedrock:*::foundation-model/*", "arn:aws:bedrock:*:${local.account}:inference-profile/*"] },
    { Sid = "Logs", Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents",
      "logs:DescribeLogStreams", "logs:DescribeLogGroups"],
    Resource = ["arn:aws:logs:${local.region}:${local.account}:log-group:/aws/bedrock-agentcore/*"] },
    { Sid = "Traces", Effect = "Allow", Action = ["xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules", "xray:GetSamplingTargets"], Resource = "*" },
    { Sid = "Metrics", Effect = "Allow", Action = "cloudwatch:PutMetricData", Resource = "*",
    Condition = { StringEquals = { "cloudwatch:namespace" = "bedrock-agentcore" } } },
    ], var.guardrail.enabled ? [
    { Sid = "Guardrail", Effect = "Allow", Action = "bedrock:ApplyGuardrail", Resource = aws_bedrock_guardrail.this[0].guardrail_arn },
  ] : []) })
}

resource "aws_bedrockagentcore_agent_runtime" "agent" {
  count              = local.runtime ? 1 : 0
  agent_runtime_name = "${local.ident}_chat"
  description        = "Chat agent: questions answered from the knowledge graph, every statement grounded in a cited passage"
  role_arn           = aws_iam_role.runtime.arn
  agent_runtime_artifact {
    container_configuration { container_uri = var.agent_image_uri }
  }
  network_configuration { network_mode = "PUBLIC" }
  protocol_configuration { server_protocol = "HTTP" }
  authorizer_configuration {
    custom_jwt_authorizer {
      discovery_url   = var.discovery_url
      allowed_clients = var.allowed_client_ids
    }
  }
  request_header_configuration { request_header_allowlist = ["Authorization"] }
  lifecycle_configuration {
    idle_runtime_session_timeout = 900
    max_lifetime                 = 3600
  }
  environment_variables = merge({
    GATEWAY_MCP_URL   = aws_bedrockagentcore_gateway.this.gateway_url
    AGENT_MODEL_ID    = var.agent_model_id
    AWS_REGION        = local.region
    MAX_TOOL_CALLS    = tostring(var.valves.max_tool_calls)
    MAX_MODEL_CALLS   = tostring(var.valves.max_model_calls)
    MAX_OUTPUT_TOKENS = tostring(var.valves.max_output_tokens)
    GROUNDING_REPAIRS = tostring(var.valves.grounding_repairs)
    }, var.guardrail.enabled ? {
    GUARDRAIL_ID      = aws_bedrock_guardrail.this[0].guardrail_id
    GUARDRAIL_VERSION = aws_bedrock_guardrail_version.this[0].version
  } : {})
  depends_on = [aws_iam_role_policy.runtime]
  tags       = var.tags
}

resource "aws_bedrockagentcore_agent_runtime_endpoint" "prod" {
  count                 = local.runtime && var.prod_version != "" ? 1 : 0
  name                  = "prod"
  agent_runtime_id      = aws_bedrockagentcore_agent_runtime.agent[0].agent_runtime_id
  agent_runtime_version = var.prod_version
  description           = "Pinned to a tested version; DEFAULT follows the latest"
  tags                  = var.tags
}

output "gateway_url" { value = aws_bedrockagentcore_gateway.this.gateway_url }
output "gateway_id" { value = aws_bedrockagentcore_gateway.this.gateway_id }
output "runtime_arn" { value = try(aws_bedrockagentcore_agent_runtime.agent[0].agent_runtime_arn, "") }
output "runtime_qualifier" { value = local.runtime && var.prod_version != "" ? "prod" : "DEFAULT" }
output "guardrail_id" { value = try(aws_bedrock_guardrail.this[0].guardrail_id, "") }
output "tool_functions" { value = { graph = aws_lambda_function.graph.function_name, passages = aws_lambda_function.passages.function_name } }
