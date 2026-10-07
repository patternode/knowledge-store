# The passages' vector index: a Bedrock Knowledge Base over S3 Vectors.
#
#   the pipeline writes every passage to kb/passages/<collection>/<passage id>.txt in the lake,
#   with a .metadata.json beside it (passage id, document, collection, scope, title), and starts
#   an ingestion job when any changed
#   chunking is NONE: one passage is one vector, so a search hit is a passage id, the same id the
#   knowledge graph's facts cite; the passage tool filters by collection and, for callers outside
#   the private scope, by scope
#
# Why a vector index at all, when the agent queries a knowledge graph: the graph is reached through
# names and ontology terms, and people often describe a situation instead ("the customer's card
# was kept by the machine abroad"). Search by meaning finds the passage, and its id leads to the
# facts that cite it. S3 Vectors has no idle floor (cents a month at this size), where an
# OpenSearch Serverless index costs hundreds of dollars a month idle.
#
# The embedding model and dimension are fixed at first deploy: changing them replaces the index,
# and the next ingestion job embeds every passage again.

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.66" }
  }
}

variable "name" { type = string }
variable "lake_bucket_arn" { type = string }
variable "embedding_model_id" {
  type    = string
  default = "amazon.titan-embed-text-v2:0"
}
variable "embedding_dimensions" {
  type    = number
  default = 1024
}
variable "permissions_boundary" {
  type        = string
  default     = null
  description = "an IAM policy ARN set as the permissions boundary of every role this module creates; null for none"
}
variable "tags" {
  type    = map(string)
  default = {}
}

data "aws_region" "current" {}
data "aws_caller_identity" "me" {}

locals {
  region        = data.aws_region.current.region
  embedding_arn = "arn:aws:bedrock:${local.region}::foundation-model/${var.embedding_model_id}"
}

resource "aws_s3vectors_vector_bucket" "this" {
  vector_bucket_name = "${var.name}-vectors-${data.aws_caller_identity.me.account_id}"
  tags               = var.tags
}

resource "aws_s3vectors_index" "passages" {
  index_name         = "passages"
  vector_bucket_name = aws_s3vectors_vector_bucket.this.vector_bucket_name
  data_type          = "float32"
  dimension          = var.embedding_dimensions
  distance_metric    = "cosine"
  # Bedrock stores the chunk text and its own metadata with each vector. Both can exceed the
  # filterable-metadata limit, so they are non-filterable; our keys (collection, scope, ...) stay filterable.
  metadata_configuration {
    non_filterable_metadata_keys = ["AMAZON_BEDROCK_TEXT", "AMAZON_BEDROCK_METADATA"]
  }
  tags = var.tags
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.me.account_id]
    }
  }
}

resource "aws_iam_role" "kb" {
  name                 = "${var.name}-knowledge-base"
  permissions_boundary = var.permissions_boundary
  assume_role_policy   = data.aws_iam_policy_document.assume.json
  tags                 = var.tags
}

resource "aws_iam_role_policy" "kb" {
  role = aws_iam_role.kb.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["bedrock:InvokeModel"], Resource = [local.embedding_arn] },
      { Effect = "Allow", Action = ["s3:GetObject"], Resource = ["${var.lake_bucket_arn}/kb/*"] },
      { Effect = "Allow", Action = ["s3:ListBucket"], Resource = [var.lake_bucket_arn],
      Condition = { StringLike = { "s3:prefix" = ["kb/*"] } } },
      { Effect = "Allow", Action = ["s3vectors:PutVectors", "s3vectors:GetVectors", "s3vectors:DeleteVectors",
      "s3vectors:QueryVectors", "s3vectors:GetIndex"], Resource = [aws_s3vectors_index.passages.index_arn] },
    ]
  })
}

resource "aws_bedrockagent_knowledge_base" "this" {
  name     = "${var.name}-passages"
  role_arn = aws_iam_role.kb.arn
  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = local.embedding_arn
      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = var.embedding_dimensions
          embedding_data_type = "FLOAT32"
        }
      }
    }
  }
  storage_configuration {
    type = "S3_VECTORS"
    s3_vectors_configuration { index_arn = aws_s3vectors_index.passages.index_arn }
  }
  tags       = var.tags
  depends_on = [aws_iam_role_policy.kb]
}

resource "aws_bedrockagent_data_source" "passages" {
  knowledge_base_id    = aws_bedrockagent_knowledge_base.this.id
  name                 = "passages"
  data_deletion_policy = "DELETE"
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn         = var.lake_bucket_arn
      inclusion_prefixes = ["kb/passages/"]
    }
  }
  vector_ingestion_configuration {
    chunking_configuration { chunking_strategy = "NONE" }
  }
}

output "knowledge_base_id" { value = aws_bedrockagent_knowledge_base.this.id }
output "knowledge_base_arn" { value = aws_bedrockagent_knowledge_base.this.arn }
output "data_source_id" { value = aws_bedrockagent_data_source.passages.data_source_id }
