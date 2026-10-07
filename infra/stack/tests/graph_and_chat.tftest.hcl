# The knowledge graph (Neptune) and the passages' Knowledge Base are on by default, and both can
# be switched off for a small demo, which then answers from the lake's projection. Mocked
# providers: no AWS account needed.
mock_provider "aws" {
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_region" {
    defaults = { name = "us-east-1", region = "us-east-1" }
  }
  mock_data "aws_availability_zones" {
    defaults = { names = ["us-east-1a", "us-east-1b"] }
  }
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{}" }
  }
}
mock_provider "archive" {}

variables {
  admin_email = "admin@example.org"
}

run "graph_and_vectors_by_default" {
  command = plan
  assert {
    condition     = module.knowledge_store.knowledge_graph != null && module.knowledge_store.knowledge_base != null
    error_message = "Neptune and the Knowledge Base should be deployed by default"
  }
}

run "a_small_demo_without_them" {
  command = plan
  variables {
    knowledge_graph = { enabled = false }
    knowledge_base  = { enabled = false }
    guardrail       = { enabled = false }
  }
  assert {
    condition     = module.knowledge_store.knowledge_graph == null && module.knowledge_store.knowledge_base == null
    error_message = "with both off, neither should be deployed"
  }
}

run "the_agent_waits_for_its_image" {
  command = plan
  assert {
    condition     = module.knowledge_store.agent.runtime_arn == "" && module.knowledge_store.agent.qualifier == "DEFAULT"
    error_message = "the Runtime is created only with agent.runtime = true"
  }
}
