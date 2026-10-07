# A collection's ontology_dir reaches the lake as config/ontology/, and a directory without
# ontology.ttl is refused before anything is planned. Mocked providers: no AWS account needed.
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

run "provided_ontology_is_uploaded" {
  command = plan
  variables {
    collections = { missions = { ontology_dir = "tests/fixtures/ontology" } }
  }
  assert {
    condition     = jsonencode(module.knowledge_store.provided_ontologies) == jsonencode({ missions = ["ontology.ttl"] })
    error_message = "the provided ontology (and only ontology.ttl) should be uploaded for missions"
  }
}

run "missing_ontology_is_refused" {
  command = plan
  variables {
    collections = { missions = { ontology_dir = "tests/fixtures/nowhere" } }
  }
  expect_failures = [var.collections]
}
