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
    condition     = module.knowledge_store.answering.adapters.runtime_arn == "" && module.knowledge_store.answering.adapters.qualifier == "DEFAULT"
    error_message = "the Runtime is created only with agent.runtime = true"
  }
}

run "the_agent_limits_each_caller_and_its_model" {
  command = plan
  variables {
    daily_questions = 25
  }
  assert {
    condition     = module.knowledge_store.answering.adapters.invocation_limit == 50
    error_message = "by default the agent allows twice daily_questions per person per day"
  }
  assert {
    condition = toset(module.knowledge_store.answering.adapters.model_grants) == toset([
      "arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-5",
      "arn:aws:bedrock:us-east-1:123456789012:inference-profile/us.anthropic.claude-sonnet-5",
    ])
    error_message = "the Runtime may call only the configured model's inference profile and its foundation model"
  }
}

run "the_agent_limit_can_be_set_or_off" {
  command = plan
  variables {
    agent = { daily_invocations = 0, model_id = "anthropic.claude-sonnet-5" }
  }
  assert {
    condition     = module.knowledge_store.answering.adapters.invocation_limit == 0
    error_message = "daily_invocations = 0 turns the agent's own limit off"
  }
  assert {
    condition     = toset(module.knowledge_store.answering.adapters.model_grants) == toset(["arn:aws:bedrock:*::foundation-model/anthropic.claude-sonnet-5"])
    error_message = "a foundation model id is granted as itself, with no inference profile"
  }
}
