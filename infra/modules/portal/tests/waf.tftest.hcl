# Offline checks of the portal's edge protection, against a mocked AWS provider:
#   terraform init -backend=false && terraform test   (in infra/modules/portal)

mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_region" {
    defaults = { region = "us-east-1" }
  }
  mock_resource "aws_apigatewayv2_api" {
    defaults = {
      api_endpoint  = "https://abc123.execute-api.us-east-1.amazonaws.com"
      execution_arn = "arn:aws:execute-api:us-east-1:123456789012:abc123"
    }
  }
  mock_resource "aws_lambda_function" {
    defaults = { invoke_arn = "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:123456789012:function:ks-portal-api/invocations" }
  }
  mock_resource "aws_cloudfront_distribution" {
    defaults = { arn = "arn:aws:cloudfront::123456789012:distribution/EXAMPLE" }
  }
  mock_resource "aws_s3_bucket" {
    defaults = { arn = "arn:aws:s3:::ks-site-123456789012" }
  }
  mock_resource "aws_iam_role" {
    defaults = { arn = "arn:aws:iam::123456789012:role/ks-portal-api" }
  }
  mock_resource "aws_dynamodb_table" {
    defaults = { arn = "arn:aws:dynamodb:us-east-1:123456789012:table/ks-chat" }
  }
  mock_resource "aws_wafv2_web_acl" {
    defaults = { arn = "arn:aws:wafv2:us-east-1:123456789012:global/webacl/ks-portal/abc" }
  }
}

variables {
  name            = "ks"
  package_root    = "../../../src"
  portal_dir      = "../../../portal"
  lake_bucket     = "ks-lake"
  lake_bucket_arn = "arn:aws:s3:::ks-lake"
  chat_model_id   = "model"
}

run "off_by_default" {
  command = apply
  assert {
    condition     = length(aws_wafv2_web_acl.portal) == 0 && aws_cloudfront_distribution.this.web_acl_id == null
    error_message = "without waf or web_acl_arn the distribution has no web ACL"
  }
  assert {
    condition     = aws_apigatewayv2_stage.default.default_route_settings[0].throttling_rate_limit == 20
    error_message = "the stage keeps its default throttling"
  }
}

run "created" {
  command = apply
  variables {
    waf = { enabled = true }
  }
  assert {
    condition     = aws_wafv2_web_acl.portal[0].scope == "CLOUDFRONT" && aws_wafv2_web_acl.portal[0].region == "us-east-1"
    error_message = "the web ACL is CLOUDFRONT scope in us-east-1"
  }
  assert {
    condition     = aws_cloudfront_distribution.this.web_acl_id == aws_wafv2_web_acl.portal[0].arn
    error_message = "the created web ACL is attached"
  }
  assert {
    condition     = length(aws_wafv2_web_acl.portal[0].rule) == 4
    error_message = "four rules: methods, API rate, overall rate, common rule set"
  }
}

run "existing" {
  command = apply
  variables {
    waf         = { enabled = true }
    web_acl_arn = "arn:aws:wafv2:us-east-1:123456789012:global/webacl/existing/def"
  }
  assert {
    condition     = length(aws_wafv2_web_acl.portal) == 0
    error_message = "an existing web ACL means none is created"
  }
  assert {
    condition     = aws_cloudfront_distribution.this.web_acl_id == "arn:aws:wafv2:us-east-1:123456789012:global/webacl/existing/def"
    error_message = "the existing web ACL is attached"
  }
}

run "bad_action" {
  command = plan
  variables {
    waf = { enabled = true, managed_rules_action = "allow" }
  }
  expect_failures = [var.waf]
}
