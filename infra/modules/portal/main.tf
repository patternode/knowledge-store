# The portal: the chat page and its API on one CloudFront URL.
#
#   CloudFront  /*      -> private S3 bucket (index.html, app.js, styles.css, config.json)
#               /api/*  -> API Gateway HTTP API (Cognito JWT authorizer) -> portal Lambda
#   Lambda      takes each question, checks the person's daily quota, and answers it
#               asynchronously (DynamoDB holds answers and quotas): with agent_runtime_arn set,
#               by asking the chat agent on AgentCore Runtime as that person (their own access
#               token); without it, with the portal's own tool loop over the lake's projection
#               GET /api/document gives a person a short-lived link to a source document they
#               may read
#
# Every API route needs a signed-in user: API Gateway checks the Cognito token before the Lambda
# runs. The page signs in with Cognito's managed login (code flow with PKCE). The Lambda is a zip
# built from source by Terraform (stdlib and boto3 only), so the first apply needs no image.
# Valves: daily_questions per person, and reserved_concurrency on the Lambda.

terraform {
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 6.66" }
    archive = { source = "hashicorp/archive", version = "~> 2.7" }
  }
}

variable "name" { type = string }
variable "package_root" {
  type        = string
  description = "the src directory holding the knowledge-store package, zipped as the Lambda's code"
}
variable "portal_dir" {
  type        = string
  description = "the static page's files"
}
variable "brand_name" {
  type    = string
  default = "Knowledge Store"
}
variable "lake_bucket" { type = string }
variable "lake_bucket_arn" { type = string }
variable "cognito_issuer" {
  type    = string
  default = ""
}
variable "cognito_client_id" {
  type    = string
  default = ""
}
variable "cognito_domain_url" {
  type    = string
  default = ""
}
variable "private_group" {
  type    = string
  default = "private-readers"
}
variable "llm_provider" {
  type    = string
  default = "bedrock"
}
variable "anthropic_api_key_secret_arn" {
  type    = string
  default = ""
}
variable "chat_model_id" { type = string }
variable "daily_questions" {
  type    = number
  default = 30
}
variable "agent_runtime_arn" {
  type        = string
  default     = ""
  description = "the chat agent; empty answers with the portal's own tool loop"
}
variable "agent_runtime_qualifier" {
  type    = string
  default = "DEFAULT"
}
variable "reserved_concurrency" {
  type        = number
  default     = 20
  description = "at most this many API requests and answers at once; -1 for no reservation, 0 turns the API off"
}
variable "log_retention_days" {
  type    = number
  default = 30
}
variable "tags" {
  type    = map(string)
  default = {}
}

data "aws_caller_identity" "me" {}
data "aws_region" "current" {}

locals {
  anthropic = var.llm_provider == "anthropic" && var.anthropic_api_key_secret_arn != ""
  mime = { html = "text/html; charset=utf-8", js = "text/javascript; charset=utf-8", css = "text/css; charset=utf-8",
  json = "application/json", svg = "image/svg+xml", png = "image/png", ico = "image/x-icon" }
  site_files = [for f in fileset(var.portal_dir, "**") : f if !startswith(f, "config.") && !endswith(f, ".md")]
  # the lake layers the API serves, under each collections/<id>/ (see src/knowledge_store/layout.py)
  served_prefixes = ["gold", "portal", "ontology", "config", "silver", "bronze"]
}

# --- static site --------------------------------------------------------------------------

resource "aws_s3_bucket" "site" {
  bucket        = "${var.name}-site-${data.aws_caller_identity.me.account_id}"
  force_destroy = true
  tags          = var.tags
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "site" {
  for_each     = toset(local.site_files)
  bucket       = aws_s3_bucket.site.id
  key          = each.key
  source       = "${var.portal_dir}/${each.key}"
  etag         = filemd5("${var.portal_dir}/${each.key}")
  content_type = lookup(local.mime, reverse(split(".", each.key))[0], "application/octet-stream")
}

resource "aws_s3_object" "config" {
  bucket = aws_s3_bucket.site.id
  key    = "config.json"
  content = jsonencode({
    mode        = "hosted"
    brand       = { name = var.brand_name }
    apiBase     = "/api"
    redirectUri = "https://${aws_cloudfront_distribution.this.domain_name}/"
    cognito     = { domain = var.cognito_domain_url, clientId = var.cognito_client_id }
  })
  content_type  = "application/json"
  cache_control = "no-cache"
}

resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "${var.name}-site"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

data "aws_cloudfront_cache_policy" "optimized" { name = "Managed-CachingOptimized" }

# CloudFront forwards Authorization on GET only when it is in the cache key, which the managed
# CachingDisabled policy cannot hold. This policy keys on it (so no answer is ever served to
# another user) with a zero default TTL; the API also sends cache-control: no-store.
resource "aws_cloudfront_cache_policy" "api" {
  name        = "${var.name}-api"
  min_ttl     = 0
  default_ttl = 0
  max_ttl     = 1
  parameters_in_cache_key_and_forwarded_to_origin {
    headers_config {
      header_behavior = "whitelist"
      headers { items = ["Authorization"] }
    }
    query_strings_config { query_string_behavior = "all" }
    cookies_config { cookie_behavior = "none" }
  }
}
data "aws_cloudfront_origin_request_policy" "all_but_host" { name = "Managed-AllViewerExceptHostHeader" }
data "aws_cloudfront_response_headers_policy" "security" { name = "Managed-SecurityHeadersPolicy" }

resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  comment             = "${var.name} portal"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"

  origin {
    origin_id                = "site"
    domain_name              = aws_s3_bucket.site.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }
  origin {
    origin_id   = "api"
    domain_name = replace(aws_apigatewayv2_api.this.api_endpoint, "https://", "")
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }
  default_cache_behavior {
    target_origin_id           = "site"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    cache_policy_id            = data.aws_cloudfront_cache_policy.optimized.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.security.id
    compress                   = true
  }
  ordered_cache_behavior {
    path_pattern               = "/api/*"
    target_origin_id           = "api"
    viewer_protocol_policy     = "https-only"
    allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods             = ["GET", "HEAD"]
    cache_policy_id            = aws_cloudfront_cache_policy.api.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.all_but_host.id
    response_headers_policy_id = data.aws_cloudfront_response_headers_policy.security.id
  }
  restrictions {
    geo_restriction { restriction_type = "none" }
  }
  viewer_certificate { cloudfront_default_certificate = true }
  tags = var.tags
}

resource "aws_s3_bucket_policy" "site" {
  bucket = aws_s3_bucket.site.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Effect    = "Allow", Principal = { Service = "cloudfront.amazonaws.com" }, Action = "s3:GetObject",
    Resource  = "${aws_s3_bucket.site.arn}/*",
    Condition = { StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.this.arn } }
  }] })
  depends_on = [aws_s3_bucket_public_access_block.site]
}

# --- API ----------------------------------------------------------------------------------

resource "aws_dynamodb_table" "chat" {
  name         = "${var.name}-chat"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  attribute {
    name = "pk"
    type = "S"
  }
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
  tags = var.tags
}

data "archive_file" "api" {
  type        = "zip"
  source_dir  = var.package_root
  output_path = "${path.root}/.build/${var.name}-api.zip"
  excludes    = ["knowledge_store.egg-info", "knowledge_store.egg-info/**", "**/__pycache__/**", "**/*.pyc"]
}

resource "aws_iam_role" "api" {
  name = "${var.name}-portal-api"
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{
  Effect = "Allow", Principal = { Service = "lambda.amazonaws.com" }, Action = "sts:AssumeRole" }] })
  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "api_logs" {
  role       = aws_iam_role.api.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "api" {
  role = aws_iam_role.api.id
  policy = jsonencode({ Version = "2012-10-17", Statement = concat([
    # Every collection's data is under collections/<id>/. The portal reads the served layers:
    # gold's projection, the status, published ontologies and drafts, config, and the documents
    # in silver and bronze, which it reads only to sign a link to a document after checking the
    # person may read it. ListBucket on the same prefixes also makes a missing key a 404 rather
    # than a 403.
    { Sid = "ReadLake", Effect = "Allow", Action = "s3:GetObject",
      Resource = concat(["${var.lake_bucket_arn}/config/*"],
    [for p in local.served_prefixes : "${var.lake_bucket_arn}/collections/*/${p}/*"]) },
    { Sid = "ListLake", Effect = "Allow", Action = "s3:ListBucket", Resource = var.lake_bucket_arn,
    Condition = { StringLike = { "s3:prefix" = concat(["config/*"], [for p in local.served_prefixes : "collections/*/${p}/*"]) } } },
    { Sid = "Chat", Effect = "Allow", Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"],
    Resource = aws_dynamodb_table.chat.arn },
    { Sid = "Models", Effect = "Allow", Action = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      Resource = ["arn:aws:bedrock:*::foundation-model/*",
    "arn:aws:bedrock:*:${data.aws_caller_identity.me.account_id}:inference-profile/*"] },
    { Sid = "SelfInvoke", Effect = "Allow", Action = "lambda:InvokeFunction",
    Resource = "arn:aws:lambda:${data.aws_region.current.region}:${data.aws_caller_identity.me.account_id}:function:${var.name}-portal-api" },
    ], local.anthropic ? [{ Sid = "AnthropicKey", Effect = "Allow", Action = "secretsmanager:GetSecretValue",
  Resource = var.anthropic_api_key_secret_arn }] : []) })
}

resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.name}-portal-api"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_lambda_function" "api" {
  function_name                  = "${var.name}-portal-api"
  role                           = aws_iam_role.api.arn
  runtime                        = "python3.12"
  handler                        = "knowledge_store.portal_api.handler.handler"
  filename                       = data.archive_file.api.output_path
  source_code_hash               = data.archive_file.api.output_base64sha256
  timeout                        = 600
  memory_size                    = 1024
  reserved_concurrent_executions = var.reserved_concurrency
  environment {
    variables = merge({
      LAKE_BUCKET     = var.lake_bucket
      CHAT_TABLE      = aws_dynamodb_table.chat.name
      LLM_PROVIDER    = var.llm_provider
      CHAT_MODEL_ID   = var.chat_model_id
      PRIVATE_GROUP   = var.private_group
      DAILY_QUESTIONS = tostring(var.daily_questions)
      }, local.anthropic ? { ANTHROPIC_API_KEY_SECRET = var.anthropic_api_key_secret_arn } : {},
    var.agent_runtime_arn != "" ? { AGENT_RUNTIME_ARN = var.agent_runtime_arn, AGENT_RUNTIME_QUALIFIER = var.agent_runtime_qualifier } : {})
  }
  depends_on = [aws_cloudwatch_log_group.api]
  tags       = var.tags
}

resource "aws_apigatewayv2_api" "this" {
  name          = "${var.name}-portal"
  protocol_type = "HTTP"
  tags          = var.tags
}

resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.this.id
  name             = "cognito"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  jwt_configuration {
    issuer   = var.cognito_issuer
    audience = [var.cognito_client_id]
  }
}

resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 29000
}

resource "aws_apigatewayv2_route" "api" {
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = "ANY /api/{proxy+}"
  target             = "integrations/${aws_apigatewayv2_integration.api.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit = 50
    throttling_rate_limit  = 20
  }
  tags = var.tags
}

resource "aws_lambda_permission" "api" {
  statement_id  = "apigw"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.this.execution_arn}/*/*"
}

output "url" { value = "https://${aws_cloudfront_distribution.this.domain_name}/" }
output "domain_name" { value = aws_cloudfront_distribution.this.domain_name }
output "distribution_id" { value = aws_cloudfront_distribution.this.id }
output "site_bucket" { value = aws_s3_bucket.site.id }
output "api_function" { value = aws_lambda_function.api.function_name }
