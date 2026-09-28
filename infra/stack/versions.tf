terraform {
  required_version = ">= 1.10.0"

  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 6.66" }
    archive = { source = "hashicorp/archive", version = "~> 2.7" }
  }

  # Partial configuration: bucket and region come from backend.hcl, which ../bootstrap writes.
  #   terraform init -backend-config=backend.hcl
  # S3-native locking (use_lockfile) needs no DynamoDB table.
  backend "s3" {
    key          = "knowledge-store/terraform.tfstate"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region  = var.region
  profile = var.aws_profile == "" ? null : var.aws_profile

  # With account_id set, refuse to apply into any other account.
  allowed_account_ids = var.account_id == "" ? null : [var.account_id]

  default_tags {
    tags = merge({ project = var.name, managed-by = "terraform", stack = "knowledge-store" }, var.extra_tags)
  }
}
