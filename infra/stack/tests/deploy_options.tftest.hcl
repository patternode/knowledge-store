# The inputs a deployment into an existing AWS estate sets: its own network or one it brings, a
# NAT gateway, a portal domain, a permissions boundary and log retention. Mocked providers: no
# AWS account needed.
mock_provider "aws" {
  # Known at plan, so the outputs built from subnets and security groups can be checked.
  override_during = plan
  mock_resource "aws_subnet" {
    defaults = { id = "subnet-own" }
  }
  mock_resource "aws_security_group" {
    defaults = { id = "sg-mock" }
  }
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_region" {
    defaults = { name = "us-east-1", region = "us-east-1" }
  }
  mock_data "aws_availability_zones" {
    defaults = { names = ["us-east-1a", "us-east-1b", "us-east-1c"] }
  }
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{}" }
  }
}
mock_provider "archive" {}

variables {
  admin_email = "admin@example.org"
}

run "own_vpc_by_default_with_tasks_in_public_subnets" {
  command = plan
  assert {
    condition     = strcontains(module.knowledge_store.run_now, "assignPublicIp=ENABLED")
    error_message = "without a NAT the pipeline's tasks run in public subnets with a public IP"
  }
}

run "nat_moves_tasks_to_private_subnets" {
  command = plan
  variables {
    network = { cidr = "10.80.0.0/16", az_count = 3, enable_nat = true }
  }
  assert {
    condition     = strcontains(module.knowledge_store.run_now, "assignPublicIp=DISABLED")
    error_message = "with a NAT the pipeline's tasks run without a public IP"
  }
}

run "an_existing_vpc_is_used_as_given" {
  command = plan
  variables {
    network = {
      existing = {
        vpc_id              = "vpc-0abc"
        private_subnet_ids  = ["subnet-priv-a", "subnet-priv-b"]
        pipeline_subnet_ids = ["subnet-app-a", "subnet-app-b"]
      }
    }
  }
  assert {
    condition     = strcontains(module.knowledge_store.run_now, "subnets=[subnet-app-a,subnet-app-b]") && strcontains(module.knowledge_store.run_now, "assignPublicIp=DISABLED")
    error_message = "the pipeline should run in the given subnets, without a public IP unless asked"
  }
  assert {
    condition     = module.knowledge_store.knowledge_graph != null
    error_message = "Neptune should still be deployed, into the given private subnets"
  }
}

run "an_existing_vpc_needs_two_private_subnets" {
  command = plan
  variables {
    network = { existing = { vpc_id = "vpc-0abc", private_subnet_ids = ["subnet-priv-a"], pipeline_subnet_ids = ["subnet-app-a"] } }
  }
  expect_failures = [var.network]
}

run "portal_on_a_custom_domain" {
  command = plan
  variables {
    portal_domain = { name = "knowledge.example.org", certificate_arn = "arn:aws:acm:us-east-1:123456789012:certificate/abc" }
  }
  assert {
    condition     = module.knowledge_store.portal_url == "https://knowledge.example.org/"
    error_message = "the portal URL should be the custom domain"
  }
}

run "the_certificate_must_be_in_us_east_1" {
  command = plan
  variables {
    portal_domain = { name = "knowledge.example.org", certificate_arn = "arn:aws:acm:eu-west-1:123456789012:certificate/abc" }
  }
  expect_failures = [var.portal_domain]
}

run "boundary_and_retention" {
  command = plan
  variables {
    permissions_boundary = "arn:aws:iam::123456789012:policy/workload-boundary"
    log_retention_days   = 90
  }
}

run "retention_must_be_a_cloudwatch_value" {
  command = plan
  variables {
    log_retention_days = 45
  }
  expect_failures = [var.log_retention_days]
}
