# The example task agent, and the AgentCore services it uses, each for a job it has:
#
#   Gateway            the knowledge tools over MCP (a Lambda target), with
#     interceptor      a REQUEST Lambda that writes the caller's scope into every tool call, and
#     policy engine    Cedar policies: the tools for signed-in callers, private content only for
#                      callers whose token carries the group or scope (checked apart from the
#                      interceptor, so a bug in one does not leak by itself)
#   Identity           inbound: Cognito tokens (people and applications) on Runtime and Gateway;
#                      outbound: an OAuth2 credential provider (token vault) for the agent's own
#                      client-credentials identity, used when it acts as itself
#   Memory             session events plus long-term strategies: facts, preferences, summaries
#   Code Interpreter   a custom interpreter in SANDBOX mode (no network) for computing over facts
#   Browser            optional (browser_enabled): open-web corroboration, sessions recorded to S3
#   Runtime            the agent container; a prod endpoint pins a version (prod_version)
#   Observability      optional (transaction_search): the account-wide switch that sends spans to
#                      CloudWatch; online evaluation needs it
#   Evaluations        optional (evaluations_enabled): built-in and one custom LLM-judge
#                      evaluator over a sample of the agent's sessions
#   Registry           optional (registry_enabled): an Agent Registry to publish the agent and its
#                      tools in; records are added after apply (no Terraform resource for them)
#   Harness            optional (harness_enabled): the same job as configuration, no container,
#                      for comparing a managed agent loop with the Strands agent
#
# Two applies: the Runtime needs its image, which CodeBuild builds after the first apply. Set
# runtime_enabled = true once the agent image exists in ECR.

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
variable "tool_schema_path" {
  type        = string
  description = "src/knowledge_store/tools/schema.json: the Gateway's tool schema, kept in step with the code by a test"
}
variable "lake_bucket" { type = string }
variable "lake_bucket_arn" { type = string }
variable "discovery_url" { type = string }
variable "allowed_client_ids" {
  type        = list(string)
  description = "Cognito app clients whose access tokens the Runtime and Gateway accept"
}
variable "agent_client_id" {
  type        = string
  description = "the agent's own machine client (client credentials, tools.public)"
}
variable "agent_client_secret" {
  type      = string
  sensitive = true
}
variable "scope_prefix" { type = string }
variable "private_group" {
  type    = string
  default = "private-readers"
}
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
variable "judge_model_id" { type = string }
variable "policy_mode" {
  type    = string
  default = "ENFORCE"
  validation {
    condition     = contains(["ENFORCE", "LOG_ONLY"], var.policy_mode)
    error_message = "policy_mode is ENFORCE or LOG_ONLY."
  }
}
variable "browser_enabled" {
  type    = bool
  default = false
}
variable "transaction_search" {
  type        = bool
  default     = false
  description = "ACCOUNT-WIDE: send X-Ray spans to CloudWatch Logs. Leave false if the account already has it on"
}
variable "evaluations_enabled" {
  type    = bool
  default = false
}
variable "evaluation_sampling_percentage" {
  type    = number
  default = 25
}
variable "registry_enabled" {
  type    = bool
  default = false
}
variable "harness_enabled" {
  type    = bool
  default = false
}
variable "memory_expiry_days" {
  type    = number
  default = 30
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
  region    = data.aws_region.current.region
  account   = data.aws_caller_identity.me.account_id
  ident     = replace(var.name, "-", "_")
  target    = "knowledge"
  read_keys = concat(["${var.lake_bucket_arn}/config/*"], [for p in ["gold", "portal", "ontology", "config"] : "${var.lake_bucket_arn}/collections/*/${p}/*"])
  list_pfx  = concat(["config/*"], [for p in ["gold", "portal", "ontology", "config"] : "collections/*/${p}/*"])
  runtime   = var.runtime_enabled && var.agent_image_uri != ""
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

resource "aws_iam_role" "tools" {
  name               = "${var.name}-agent-tools"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "tools_logs" {
  role       = aws_iam_role.tools.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "tools" {
  role = aws_iam_role.tools.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Sid = "ReadServedLayers", Effect = "Allow", Action = "s3:GetObject", Resource = local.read_keys },
    { Sid = "ListServedLayers", Effect = "Allow", Action = "s3:ListBucket", Resource = var.lake_bucket_arn,
    Condition = { StringLike = { "s3:prefix" = local.list_pfx } } },
  ] })
}

resource "aws_lambda_function" "tools" {
  function_name    = "${var.name}-agent-tools"
  role             = aws_iam_role.tools.arn
  runtime          = "python3.12"
  handler          = "knowledge_store.tools.gateway.lambda_handler"
  filename         = data.archive_file.code.output_path
  source_code_hash = data.archive_file.code.output_base64sha256
  timeout          = 60
  memory_size      = 1024
  environment { variables = { LAKE_BUCKET = var.lake_bucket } }
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

# --- Gateway, target, policy engine --------------------------------------------------------

resource "aws_s3_object" "tool_schema" {
  bucket       = var.lake_bucket
  key          = "agentcore/tool-schemas/${local.target}.json"
  source       = var.tool_schema_path
  etag         = filemd5(var.tool_schema_path)
  content_type = "application/json"
}

resource "aws_bedrockagentcore_policy_engine" "this" {
  name        = "${local.ident}_policies"
  description = "Who may call the knowledge tools, and for which scope of content"
  tags        = var.tags
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
    Resource = [aws_lambda_function.tools.arn, aws_lambda_function.interceptor.arn] },
    { Sid = "ToolSchema", Effect = "Allow", Action = "s3:GetObject", Resource = "${var.lake_bucket_arn}/agentcore/tool-schemas/*" },
    { Sid    = "PolicyEngine", Effect = "Allow",
      Action = ["bedrock-agentcore:GetPolicyEngine", "bedrock-agentcore:AuthorizeAction", "bedrock-agentcore:PartiallyAuthorizeActions"],
      Resource = [aws_bedrockagentcore_policy_engine.this.policy_engine_arn,
    "arn:aws:bedrock-agentcore:${local.region}:${local.account}:gateway/*"] },
  ] })
}

resource "aws_bedrockagentcore_gateway" "this" {
  name            = "${var.name}-tools"
  description     = "The knowledge graph as read-only tools, scoped by the caller's token"
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
      search_type  = "SEMANTIC"
      instructions = "Read-only tools over ontology-typed knowledge graphs, one per collection. Call list_collections, then describe_ontology for the collection, then search and read. Cite passage ids."
    }
  }
  interceptor_configuration {
    interception_points = ["REQUEST"]
    interceptor {
      lambda { arn = aws_lambda_function.interceptor.arn }
    }
    input_configuration { pass_request_headers = true }
  }
  policy_engine_configuration {
    arn  = aws_bedrockagentcore_policy_engine.this.policy_engine_arn
    mode = var.policy_mode
  }
  depends_on = [aws_iam_role_policy.gateway]
  tags       = var.tags
}

resource "aws_bedrockagentcore_gateway_target" "knowledge" {
  name               = local.target
  gateway_identifier = aws_bedrockagentcore_gateway.this.gateway_id
  description        = "knowledge-store knowledge tools"
  credential_provider_configuration {
    gateway_iam_role {}
  }
  target_configuration {
    mcp {
      lambda {
        lambda_arn = aws_lambda_function.tools.arn
        tool_schema {
          s3 {
            uri                     = "s3://${var.lake_bucket}/${aws_s3_object.tool_schema.key}"
            bucket_owner_account_id = local.account
          }
        }
      }
    }
  }
  depends_on = [aws_iam_role_policy.gateway]
}

locals {
  gateway_resource = "AgentCore::Gateway::\"${aws_bedrockagentcore_gateway.this.gateway_arn}\""
}

# Default deny: without this, no tool can be called at all.
resource "aws_bedrockagentcore_policy" "permit_tools" {
  name             = "permit_knowledge_tools"
  policy_engine_id = aws_bedrockagentcore_policy_engine.this.policy_engine_id
  description      = "Any caller the Gateway authenticated may use the knowledge tools"
  definition {
    cedar {
      statement = "permit(principal is AgentCore::OAuthUser, action in AgentCore::Action::\"${local.target}\", resource == ${local.gateway_resource});"
    }
  }
  depends_on = [aws_bedrockagentcore_gateway_target.knowledge]
}

# The interceptor marks a call private from the token; this refuses a private call unless the
# token itself carries the entitlement, whatever the interceptor decided. context.input exists
# only on the per-tool actions (<target>___<tool>), not on the target's action group, so the
# policy names each tool in the schema.
locals {
  tool_actions = join(", ", [for t in jsondecode(file(var.tool_schema_path)) : "AgentCore::Action::\"${local.target}___${t.name}\""])
}

resource "aws_bedrockagentcore_policy" "forbid_unentitled_private" {
  name             = "forbid_unentitled_private"
  policy_engine_id = aws_bedrockagentcore_policy_engine.this.policy_engine_id
  description      = "Private-scope reads need the private group (people) or the tools.private scope (applications)"
  definition {
    cedar {
      statement = <<-CEDAR
        forbid(principal is AgentCore::OAuthUser, action in [${local.tool_actions}], resource == ${local.gateway_resource})
        when { context.input has caller_private && context.input.caller_private == true }
        unless {
          (principal.hasTag("cognito:groups") && principal.getTag("cognito:groups") like "*${var.private_group}*") ||
          (principal.hasTag("scope") && principal.getTag("scope") like "*${var.scope_prefix}/tools.private*")
        };
      CEDAR
    }
  }
  depends_on = [aws_bedrockagentcore_gateway_target.knowledge]
}

# --- Identity: the agent's own outbound credential ---------------------------------------------

resource "aws_bedrockagentcore_oauth2_credential_provider" "agent" {
  name                       = "${var.name}-agent-identity"
  credential_provider_vendor = "CustomOauth2"
  oauth2_provider_config {
    custom_oauth2_provider_config {
      client_id_wo                  = var.agent_client_id
      client_secret_wo              = var.agent_client_secret
      client_credentials_wo_version = 1
      oauth_discovery { discovery_url = var.discovery_url }
    }
  }
  tags = var.tags
}

# --- Memory ----------------------------------------------------------------------------------

resource "aws_bedrockagentcore_memory" "this" {
  name                  = "${local.ident}_memory"
  description           = "The agent's per-caller research memory"
  event_expiry_duration = var.memory_expiry_days
  tags                  = var.tags
}

resource "aws_bedrockagentcore_memory_strategy" "facts" {
  name                = "facts"
  memory_id           = aws_bedrockagentcore_memory.this.id
  type                = "SEMANTIC"
  description         = "Entities and findings a caller has researched"
  namespace_templates = ["/facts/{actorId}/"]
}

resource "aws_bedrockagentcore_memory_strategy" "preferences" {
  name                = "preferences"
  memory_id           = aws_bedrockagentcore_memory.this.id
  type                = "USER_PREFERENCE"
  description         = "How a caller likes results: length, aspects, collections"
  namespace_templates = ["/preferences/{actorId}/"]
}

resource "aws_bedrockagentcore_memory_strategy" "summaries" {
  name                = "summaries"
  memory_id           = aws_bedrockagentcore_memory.this.id
  type                = "SUMMARIZATION"
  description         = "One summary per research session"
  namespace_templates = ["/summaries/{actorId}/{sessionId}/"]
}

# --- Code Interpreter and Browser --------------------------------------------------------------

resource "aws_iam_role" "tools_exec" {
  name               = "${var.name}-agent-builtin-tools"
  assume_role_policy = data.aws_iam_policy_document.agentcore_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "tools_exec" {
  role = aws_iam_role.tools_exec.id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat([
    { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
    Resource = "arn:aws:logs:${local.region}:${local.account}:log-group:/aws/bedrock-agentcore/*" },
    ], [for st in [
      { Effect = "Allow", Action = ["s3:PutObject", "s3:GetObject", "s3:ListMultipartUploadParts", "s3:AbortMultipartUpload"],
      Resource = "${var.lake_bucket_arn}/agentcore/browser-recordings/*" },
      { Effect = "Allow", Action = ["s3:ListBucket"], Resource = var.lake_bucket_arn,
      Condition = { StringLike = { "s3:prefix" = ["agentcore/browser-recordings/*"] } } },
  ] : st if var.browser_enabled]) })
}

resource "aws_bedrockagentcore_code_interpreter" "this" {
  name               = "${local.ident}_code"
  description        = "Sandboxed computation over retrieved facts; no network"
  execution_role_arn = aws_iam_role.tools_exec.arn
  network_configuration { network_mode = "SANDBOX" }
  tags = var.tags
}

resource "aws_bedrockagentcore_browser" "this" {
  count              = var.browser_enabled ? 1 : 0
  name               = "${local.ident}_browser"
  description        = "Open-web corroboration, recorded"
  execution_role_arn = aws_iam_role.tools_exec.arn
  network_configuration { network_mode = "PUBLIC" }
  recording {
    enabled = true
    s3_location {
      bucket = var.lake_bucket
      prefix = "agentcore/browser-recordings/"
    }
  }
  # CreateBrowser checks that the role can already write the recordings.
  depends_on = [aws_iam_role_policy.tools_exec]
  tags       = var.tags
}

# --- Runtime ---------------------------------------------------------------------------------

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
      "logs:DescribeLogStreams", "logs:DescribeLogGroups", "logs:PutResourcePolicy"],
    Resource = ["arn:aws:logs:${local.region}:${local.account}:log-group:/aws/bedrock-agentcore/*", "arn:aws:logs:${local.region}:${local.account}:log-group:aws/spans:*"] },
    { Sid = "Traces", Effect = "Allow", Action = ["xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules", "xray:GetSamplingTargets"], Resource = "*" },
    { Sid = "Metrics", Effect = "Allow", Action = "cloudwatch:PutMetricData", Resource = "*",
    Condition = { StringEquals = { "cloudwatch:namespace" = "bedrock-agentcore" } } },
    { Sid = "Memory", Effect = "Allow", Action = [
      "bedrock-agentcore:CreateEvent", "bedrock-agentcore:GetEvent", "bedrock-agentcore:ListEvents", "bedrock-agentcore:ListSessions",
      "bedrock-agentcore:RetrieveMemoryRecords", "bedrock-agentcore:ListMemoryRecords", "bedrock-agentcore:GetMemoryRecord"],
    Resource = aws_bedrockagentcore_memory.this.arn },
    { Sid = "CodeInterpreter", Effect = "Allow", Action = [
      "bedrock-agentcore:StartCodeInterpreterSession", "bedrock-agentcore:InvokeCodeInterpreter", "bedrock-agentcore:StopCodeInterpreterSession",
      "bedrock-agentcore:GetCodeInterpreterSession", "bedrock-agentcore:ListCodeInterpreterSessions"],
    Resource = aws_bedrockagentcore_code_interpreter.this.code_interpreter_arn },
    { Sid = "WorkloadIdentity", Effect = "Allow", Action = [
      "bedrock-agentcore:GetWorkloadAccessToken", "bedrock-agentcore:GetWorkloadAccessTokenForJWT", "bedrock-agentcore:GetResourceOauth2Token"],
      Resource = [
        "arn:aws:bedrock-agentcore:${local.region}:${local.account}:workload-identity-directory/default",
        "arn:aws:bedrock-agentcore:${local.region}:${local.account}:workload-identity-directory/default/workload-identity/*",
        "arn:aws:bedrock-agentcore:${local.region}:${local.account}:token-vault/default",
    "arn:aws:bedrock-agentcore:${local.region}:${local.account}:token-vault/default/oauth2credentialprovider/${aws_bedrockagentcore_oauth2_credential_provider.agent.name}"] },
    { Sid = "IdentitySecret", Effect = "Allow", Action = "secretsmanager:GetSecretValue",
    Resource = aws_bedrockagentcore_oauth2_credential_provider.agent.client_secret_arn[0].secret_arn },
    ], var.browser_enabled ? [
    { Sid = "Browser", Effect = "Allow", Action = [
      "bedrock-agentcore:StartBrowserSession", "bedrock-agentcore:StopBrowserSession", "bedrock-agentcore:GetBrowserSession",
      "bedrock-agentcore:ListBrowserSessions", "bedrock-agentcore:ConnectBrowserAutomationStream", "bedrock-agentcore:UpdateBrowserStream"],
    Resource = aws_bedrockagentcore_browser.this[0].browser_arn },
  ] : []) })
}

resource "aws_bedrockagentcore_agent_runtime" "agent" {
  count              = local.runtime ? 1 : 0
  agent_runtime_name = "${local.ident}_dossier"
  description        = "Example task agent: dossier, compare and query over the knowledge graph"
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
    GATEWAY_MCP_URL         = aws_bedrockagentcore_gateway.this.gateway_url
    AGENT_MODEL_ID          = var.agent_model_id
    MEMORY_ID               = aws_bedrockagentcore_memory.this.id
    CODE_INTERPRETER_ID     = aws_bedrockagentcore_code_interpreter.this.code_interpreter_id
    AGENT_IDENTITY_PROVIDER = aws_bedrockagentcore_oauth2_credential_provider.agent.name
    SCOPE_PREFIX            = var.scope_prefix
    AWS_REGION              = local.region
  }, var.browser_enabled ? { BROWSER_ID = aws_bedrockagentcore_browser.this[0].browser_id } : {})
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

# --- Observability: account-wide, off unless asked -----------------------------------------------

resource "aws_cloudwatch_log_resource_policy" "xray" {
  count       = var.transaction_search ? 1 : 0
  policy_name = "TransactionSearchXRayAccess"
  policy_document = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect = "Allow", Principal = { Service = "xray.amazonaws.com" }, Action = "logs:PutLogEvents",
    Resource = ["arn:aws:logs:${local.region}:${local.account}:log-group:aws/spans:*",
    "arn:aws:logs:${local.region}:${local.account}:log-group:/aws/application-signals/data:*"],
    Condition = { ArnLike = { "aws:SourceArn" = "arn:aws:xray:${local.region}:${local.account}:*" },
    StringEquals = { "aws:SourceAccount" = local.account } }
  }] })
}

resource "aws_xray_trace_segment_destination" "cloudwatch" {
  count       = var.transaction_search ? 1 : 0
  destination = "CloudWatchLogs"
  depends_on  = [aws_cloudwatch_log_resource_policy.xray]
}

# --- Evaluations -----------------------------------------------------------------------------

resource "aws_iam_role" "evaluations" {
  count = local.runtime && var.evaluations_enabled ? 1 : 0
  name  = "${var.name}-agent-evaluations"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect    = "Allow", Principal = { Service = "bedrock-agentcore.amazonaws.com" }, Action = "sts:AssumeRole",
    Condition = { StringEquals = { "aws:SourceAccount" = local.account } }
  }] })
  tags = var.tags
}

resource "aws_iam_role_policy" "evaluations" {
  count = local.runtime && var.evaluations_enabled ? 1 : 0
  role  = aws_iam_role.evaluations[0].id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["logs:DescribeLogGroups", "logs:StartQuery", "logs:GetQueryResults"], Resource = "*" },
    { Effect = "Allow", Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
    Resource = "arn:aws:logs:${local.region}:${local.account}:log-group:/aws/bedrock-agentcore/evaluations/*" },
    { Effect = "Allow", Action = ["logs:DescribeIndexPolicies", "logs:PutIndexPolicy"],
    Resource = ["arn:aws:logs:${local.region}:${local.account}:log-group:aws/spans", "arn:aws:logs:${local.region}:${local.account}:log-group:/aws/bedrock-agentcore/runtimes/*"] },
    { Effect = "Allow", Action = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
    Resource = ["arn:aws:bedrock:*::foundation-model/*", "arn:aws:bedrock:*:${local.account}:inference-profile/*"] },
  ] })
}

# The agent's own promise, judged: every statement in the result is supported by what the tools returned.
resource "aws_bedrockagentcore_evaluator" "grounding" {
  count          = local.runtime && var.evaluations_enabled ? 1 : 0
  evaluator_name = "${local.ident}_citation_grounding"
  description    = "Whether each statement in the agent's result is supported by the tool results it cites"
  level          = "TRACE"
  evaluator_config {
    llm_as_a_judge {
      instructions = <<-TXT
        You are judging a research agent that must report only facts found in its tool results, each with the
        passage ids it came from. Read the tool results in the context and the agent's final answer.
        Score how well every statement in the answer is supported by a tool result it cites.
        Context: {context}
        Answer: {assistant_turn}
      TXT
      rating_scale {
        numerical {
          value      = 1
          label      = "grounded"
          definition = "Every statement is supported by a cited tool result"
        }
        numerical {
          value      = 0.5
          label      = "partly"
          definition = "Most statements are supported; some are unsupported or cite the wrong passage"
        }
        numerical {
          value      = 0
          label      = "ungrounded"
          definition = "Statements are not supported by the tool results"
        }
      }
      model_config {
        bedrock_evaluator_model_config { model_id = var.judge_model_id }
      }
    }
  }
  tags = var.tags
}

resource "aws_bedrockagentcore_online_evaluation_config" "agent" {
  count                         = local.runtime && var.evaluations_enabled ? 1 : 0
  online_evaluation_config_name = "${local.ident}_dossier_online"
  description                   = "A sample of the agent's sessions, scored after they finish"
  enable_on_create              = true
  evaluation_execution_role_arn = aws_iam_role.evaluations[0].arn
  data_source_config {
    cloudwatch_logs {
      log_group_names = ["/aws/bedrock-agentcore/runtimes/${aws_bedrockagentcore_agent_runtime.agent[0].agent_runtime_id}-DEFAULT"]
      service_names   = ["${aws_bedrockagentcore_agent_runtime.agent[0].agent_runtime_name}.DEFAULT"]
    }
  }
  evaluator { evaluator_id = "Builtin.Faithfulness" }
  evaluator { evaluator_id = "Builtin.ToolSelectionAccuracy" }
  evaluator { evaluator_id = "Builtin.GoalSuccessRate" }
  evaluator { evaluator_id = aws_bedrockagentcore_evaluator.grounding[0].evaluator_id }
  rule {
    sampling_config { sampling_percentage = var.evaluation_sampling_percentage }
    session_config { session_timeout_minutes = 15 }
  }
  depends_on = [aws_iam_role_policy.evaluations]
  tags       = var.tags
}

# --- Registry ----------------------------------------------------------------------------------

resource "aws_agentregistry_registry" "this" {
  count       = var.registry_enabled ? 1 : 0
  name        = "${var.name}-registry"
  description = "Where this deployment's agents and tools are published for other teams to find"
  discovery_configuration { authorizer_type = "AWS_IAM" }
  approval_configuration { auto_approval_rules = ["APPROVE_ALL"] }
  tags = var.tags
}

# --- Harness: the same job as configuration --------------------------------------------------------

resource "aws_bedrockagentcore_harness" "dossier" {
  count              = var.harness_enabled ? 1 : 0
  harness_name       = "${local.ident}_dossier_harness"
  execution_role_arn = aws_iam_role.runtime.arn
  max_iterations     = 24
  timeout_seconds    = 600
  # Explicit, because the API returns an empty map and a null here fails the apply with
  # "inconsistent values for sensitive attribute".
  environment_variables = {}
  model {
    bedrock_model_config {
      model_id    = var.agent_model_id
      temperature = 0
    }
  }
  system_prompt {
    text = "You are a research agent over knowledge graphs, one per collection. Call list_collections and describe_ontology first. Report only what the tools return, with the passage ids each fact comes from. Use the code interpreter for any arithmetic."
  }
  tool {
    type = "agentcore_gateway"
    name = "knowledge"
    config {
      agentcore_gateway {
        gateway_arn = aws_bedrockagentcore_gateway.this.gateway_arn
        outbound_auth {
          oauth {
            provider_arn = aws_bedrockagentcore_oauth2_credential_provider.agent.credential_provider_arn
            scopes       = ["${var.scope_prefix}/tools.public"]
            grant_type   = "CLIENT_CREDENTIALS"
          }
        }
      }
    }
  }
  tool {
    type = "agentcore_code_interpreter"
    name = "code"
    config {
      agentcore_code_interpreter { code_interpreter_arn = aws_bedrockagentcore_code_interpreter.this.code_interpreter_arn }
    }
  }
  authorizer_configuration {
    custom_jwt_authorizer {
      discovery_url   = var.discovery_url
      allowed_clients = var.allowed_client_ids
    }
  }
  tags = var.tags
}

output "gateway_url" { value = aws_bedrockagentcore_gateway.this.gateway_url }
output "gateway_id" { value = aws_bedrockagentcore_gateway.this.gateway_id }
output "memory_id" { value = aws_bedrockagentcore_memory.this.id }
output "code_interpreter_id" { value = aws_bedrockagentcore_code_interpreter.this.code_interpreter_id }
output "runtime_arn" { value = try(aws_bedrockagentcore_agent_runtime.agent[0].agent_runtime_arn, "") }
output "runtime_name" { value = try(aws_bedrockagentcore_agent_runtime.agent[0].agent_runtime_name, "") }
output "registry_arn" { value = try(aws_agentregistry_registry.this[0].registry_arn, "") }
output "harness_arn" { value = try(aws_bedrockagentcore_harness.dossier[0].arn, "") }
