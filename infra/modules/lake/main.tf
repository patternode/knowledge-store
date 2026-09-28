# Knowledge Store's lake: one bucket, layered by prefix (see
# the repository root/src/knowledge_store/layout.py, which this must match).
#
#   landing/   uploads from people and tools (the default source)
#   bronze/    immutable, content-addressed copies
#   silver/    parsed documents and passages
#   gold/      the RDF record per ontology version, and the portal's projection
#   ontology/  published versions (immutable), drafts, the candidate register
#   config/collections.json and collections/<id>/config/*.json: written here from tfvars
#   collections/<id>/{bronze,silver,gold,ontology}/: one lake per collection, same layout
#
# EventBridge notifications are on, so an upload to landing/ can start the pipeline
# (modules/pipeline). Versioning is on, so an overwrite or delete in any layer is recoverable.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.66" }
  }
}

variable "name" { type = string }
variable "collections" {
  type        = any
  description = "collection id => {sources, profile, settings}, written to collections/<id>/config/*.json"
}
variable "force_destroy" {
  type        = bool
  default     = false
  description = "allow terraform destroy to delete a lake that still holds objects"
}
variable "tags" {
  type    = map(string)
  default = {}
}

data "aws_caller_identity" "me" {}

resource "aws_s3_bucket" "lake" {
  bucket        = "${var.name}-lake-${data.aws_caller_identity.me.account_id}"
  force_destroy = var.force_destroy
  tags          = var.tags
}

resource "aws_s3_bucket_versioning" "lake" {
  bucket = aws_s3_bucket.lake.id
  versioning_configuration { status = "Enabled" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "lake" {
  bucket                  = aws_s3_bucket.lake.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_policy" "tls_only" {
  bucket = aws_s3_bucket.lake.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "DenyInsecureTransport"
      Effect    = "Deny"
      Principal = "*"
      Action    = "s3:*"
      Resource  = [aws_s3_bucket.lake.arn, "${aws_s3_bucket.lake.arn}/*"]
      Condition = { Bool = { "aws:SecureTransport" = "false" } }
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.lake]
}

resource "aws_s3_bucket_lifecycle_configuration" "lake" {
  bucket = aws_s3_bucket.lake.id
  rule {
    id     = "expire-old-versions"
    status = "Enabled"
    filter {}
    noncurrent_version_expiration { noncurrent_days = 30 }
    abort_incomplete_multipart_upload { days_after_initiation = 7 }
  }
}

resource "aws_s3_bucket_notification" "eventbridge" {
  bucket      = aws_s3_bucket.lake.id
  eventbridge = true
}

resource "aws_s3_object" "collections" {
  bucket       = aws_s3_bucket.lake.id
  key          = "config/collections.json"
  content      = jsonencode([for id in sort(keys(var.collections)) : { id = id }])
  content_type = "application/json"
}

locals {
  config_files = merge([for id, c in var.collections : {
    "${id}/sources"  = c.sources
    "${id}/profile"  = c.profile
    "${id}/settings" = c.settings
  }]...)
}

resource "aws_s3_object" "collection_config" {
  for_each     = local.config_files
  bucket       = aws_s3_bucket.lake.id
  key          = "collections/${split("/", each.key)[0]}/config/${split("/", each.key)[1]}.json"
  content      = jsonencode(each.value)
  content_type = "application/json"
}

output "bucket" { value = aws_s3_bucket.lake.id }
output "bucket_arn" { value = aws_s3_bucket.lake.arn }
