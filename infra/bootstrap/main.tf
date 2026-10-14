# Once per account: the bucket that holds the stack's Terraform state. Local state here.
#
#   terraform init && terraform apply -var account_id=123456789012
#   terraform output -raw backend_hcl > ../stack/backend.hcl
#
# If the account already has a state bucket, skip this and write ../stack/backend.hcl by hand:
#   bucket = "<bucket>"
#   region = "<region>"

terraform {
  required_version = ">= 1.10.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.66" }
  }
}

variable "account_id" { type = string }
variable "region" {
  type    = string
  default = "us-east-1"
}
variable "aws_profile" {
  type    = string
  default = ""
}
variable "bucket_prefix" {
  type    = string
  default = "knowledge-store-tfstate"
}

provider "aws" {
  region              = var.region
  profile             = var.aws_profile == "" ? null : var.aws_profile
  allowed_account_ids = [var.account_id]
}

resource "aws_s3_bucket" "state" {
  bucket = "${var.bucket_prefix}-${var.account_id}-${var.region}"
  lifecycle { prevent_destroy = true }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket                  = aws_s3_bucket.state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{
    Sid       = "DenyInsecureTransport", Effect = "Deny", Principal = "*", Action = "s3:*",
    Resource  = [aws_s3_bucket.state.arn, "${aws_s3_bucket.state.arn}/*"],
    Condition = { Bool = { "aws:SecureTransport" = "false" } }
  }] })
  depends_on = [aws_s3_bucket_public_access_block.state]
}

output "backend_hcl" {
  value = "bucket = \"${aws_s3_bucket.state.id}\"\nregion = \"${var.region}\"\n"
}
