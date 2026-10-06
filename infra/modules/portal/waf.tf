# Edge protection for the portal: an optional AWS WAF web ACL on the CloudFront distribution.
#
# A web ACL for CloudFront has scope CLOUDFRONT and must live in us-east-1, whatever region the
# rest of the stack is in. The AWS provider (6.x) takes a per-resource region, so the module needs
# no provider alias and callers pass nothing new. Instead of creating one, a caller can attach a
# web ACL it manages elsewhere (web_acl_arn), for example one created by a CloudFront pricing plan.
#
# Rules, in order:
#   allowed-methods   block any method the portal does not use (it sends GET and POST)
#   api-rate-per-ip   block an IP that sends more than api_rate_limit requests to /api/* in 5 minutes
#   rate-per-ip       block an IP that sends more than rate_limit requests in 5 minutes
#   common-rule-set   the AWS managed common rule set, blocking or only counting
#
# The chat polls /api/chat every 1.5 seconds while a question is answered (up to two minutes of
# polls for a slow answer), so the API limit leaves room for several questions in a window.

variable "waf" {
  description = "the web ACL to create; see infra/modules/knowledge-store/README.md"
  type = object({
    enabled                       = optional(bool, false)
    managed_rules_action          = optional(string, "block")
    managed_rules_count_overrides = optional(list(string), ["SizeRestrictions_BODY"])
    rate_limit                    = optional(number, 500)
    api_rate_limit                = optional(number, 300)
    allowed_methods               = optional(list(string), ["GET", "HEAD", "POST", "OPTIONS"])
  })
  default = {}
  validation {
    condition     = contains(["block", "count"], var.waf.managed_rules_action)
    error_message = "waf.managed_rules_action must be block or count."
  }
  validation {
    condition     = var.waf.rate_limit >= 10 && var.waf.api_rate_limit >= 10
    error_message = "waf.rate_limit and waf.api_rate_limit must be at least 10 (the AWS WAF minimum)."
  }
  validation {
    condition     = length(var.waf.allowed_methods) > 0 && alltrue([for m in var.waf.allowed_methods : can(regex("^[A-Z]+$", m))])
    error_message = "waf.allowed_methods must be a non-empty list of upper case HTTP methods."
  }
}

variable "web_acl_arn" {
  type        = string
  default     = ""
  description = "an existing CLOUDFRONT-scope web ACL to attach instead of creating one; it takes precedence over waf.enabled"
}

locals {
  create_waf  = var.web_acl_arn == "" && var.waf.enabled
  web_acl_arn = var.web_acl_arn != "" ? var.web_acl_arn : (local.create_waf ? aws_wafv2_web_acl.portal[0].arn : null)
  waf_metric  = replace(var.name, "-", "")
}

resource "aws_wafv2_web_acl" "portal" {
  count  = local.create_waf ? 1 : 0
  region = "us-east-1" # CLOUDFRONT scope is only served from us-east-1
  name   = "${var.name}-portal"
  scope  = "CLOUDFRONT"

  default_action {
    allow {}
  }

  rule {
    name     = "allowed-methods"
    priority = 0
    action {
      block {}
    }
    statement {
      not_statement {
        statement {
          regex_match_statement {
            regex_string = "^(${join("|", var.waf.allowed_methods)})$"
            field_to_match {
              method {}
            }
            text_transformation {
              priority = 0
              type     = "NONE"
            }
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.waf_metric}AllowedMethods"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "api-rate-per-ip"
    priority = 1
    action {
      block {}
    }
    statement {
      rate_based_statement {
        limit                 = var.waf.api_rate_limit
        aggregate_key_type    = "IP"
        evaluation_window_sec = 300
        scope_down_statement {
          byte_match_statement {
            search_string         = "/api/"
            positional_constraint = "STARTS_WITH"
            field_to_match {
              uri_path {}
            }
            text_transformation {
              priority = 0
              type     = "NONE"
            }
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.waf_metric}ApiRatePerIp"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "rate-per-ip"
    priority = 2
    action {
      block {}
    }
    statement {
      rate_based_statement {
        limit                 = var.waf.rate_limit
        aggregate_key_type    = "IP"
        evaluation_window_sec = 300
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.waf_metric}RatePerIp"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "common-rule-set"
    priority = 3
    override_action {
      dynamic "none" {
        for_each = var.waf.managed_rules_action == "block" ? [1] : []
        content {}
      }
      dynamic "count" {
        for_each = var.waf.managed_rules_action == "count" ? [1] : []
        content {}
      }
    }
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
        # Rules that only count. SizeRestrictions_BODY by default: a chat question carries the
        # recent history, which can pass the rule's 8 KB body limit.
        dynamic "rule_action_override" {
          for_each = toset(var.waf.managed_rules_count_overrides)
          content {
            name = rule_action_override.value
            action_to_use {
              count {}
            }
          }
        }
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "${local.waf_metric}CommonRuleSet"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.waf_metric}Portal"
    sampled_requests_enabled   = true
  }

  tags = var.tags
}

output "web_acl_arn" {
  value       = local.web_acl_arn
  description = "the web ACL on the distribution, or null when there is none"
}
