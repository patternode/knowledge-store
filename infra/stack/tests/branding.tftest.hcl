# The branding input reaches the site bucket as brand.css, the logo and the icon under brand/, and
# the further files, and a wrong file or path is refused before anything is planned. Mocked
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

run "nothing_by_default" {
  command = plan
  assert {
    condition     = length(module.knowledge_store.branding.assets) == 0 && length(module.knowledge_store.branding.files) == 0
    error_message = "without branding, no logo, icon or file is uploaded"
  }
  assert {
    condition     = !strcontains(module.knowledge_store.branding.css, "{")
    error_message = "without branding, brand.css holds no rule"
  }
}

run "the_brand_is_uploaded" {
  command = plan
  variables {
    branding = {
      logo        = "tests/fixtures/brand/logo.svg"
      icon        = "tests/fixtures/brand/logo.svg"
      colors      = { action = "#0a5a3c", link = "#0a5a3c" }
      colors_dark = { action = "#7fd1b0" }
      stylesheet  = "tests/fixtures/brand/brand.css"
      files       = { "brand/extra.css" = "tests/fixtures/brand/brand.css" }
    }
  }
  assert {
    condition     = jsonencode(module.knowledge_store.branding.assets) == jsonencode({ icon = "brand/icon.svg", logo = "brand/logo.svg" })
    error_message = "the logo and the icon are served under brand/ with their own extension"
  }
  assert {
    condition     = jsonencode(module.knowledge_store.branding.files) == jsonencode(["brand/extra.css"])
    error_message = "a further file is served at the path given"
  }
  assert {
    condition     = strcontains(module.knowledge_store.branding.css, ":root {\n  --action: #0a5a3c;\n  --link: #0a5a3c;\n}")
    error_message = "the light-mode tokens are written as :root rules"
  }
  assert {
    condition     = strcontains(module.knowledge_store.branding.css, "@media (prefers-color-scheme: dark) {\n  :root {\n    --action: #7fd1b0;\n  }\n}")
    error_message = "the dark-mode tokens are written under the dark media query"
  }
  assert {
    condition     = endswith(module.knowledge_store.branding.css, file("tests/fixtures/brand/brand.css"))
    error_message = "the deployment's stylesheet comes last"
  }
}

run "a_wrong_icon_is_refused" {
  command = plan
  variables {
    branding = { icon = "tests/fixtures/brand/brand.css" }
  }
  expect_failures = [var.branding]
}

run "a_missing_file_is_refused" {
  command = plan
  variables {
    branding = { logo = "tests/fixtures/brand/nowhere.svg" }
  }
  expect_failures = [var.branding]
}

run "a_file_outside_brand_is_refused" {
  command = plan
  variables {
    branding = { files = { "index.html" = "tests/fixtures/brand/brand.css" } }
  }
  expect_failures = [var.branding]
}

run "a_token_value_cannot_break_out_of_its_rule" {
  command = plan
  variables {
    branding = { colors = { action = "red; } body { display: none" } }
  }
  expect_failures = [var.branding]
}
