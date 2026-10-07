# The knowledge graph: Amazon Neptune Database, holding the lake's gold RDF as it is.
#
#   one named graph per document per ontology version in the active chain, and one for the
#   active ontology (the T-Box), loaded and kept in step by the pipeline (SPARQL UPDATE, one
#   request per graph, so each document's facts change atomically)
#   the agent's graph tools query it with fixed SPARQL built from the ontology
#
# Neptune Database rather than Neptune Analytics: it speaks SPARQL over RDF, which the ontology,
# SHACL and the lake's N-Quads already are, so nothing is converted. Its smallest instance
# (db.t4g.medium) is the cheapest graph option that is always on; serverless_min_ncu > 0 uses
# Neptune Serverless instead. The graph is a projection of the lake, rebuilt by the next sweep,
# so backups are kept for a day and no final snapshot is taken.
#
# It has no public endpoint. Only its client group (attached to the graph tools' Lambda) and the
# groups in client_security_group_ids (the pipeline's tasks) reach it, and IAM database
# authentication is on:
# each client's role says what it may do (the tools may only read).

terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 6.66" }
  }
}

variable "name" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "client_security_group_ids" {
  type        = map(string)
  description = "name => security group allowed to connect on 8182 (keys must be known at plan)"
}
variable "instance_class" {
  type    = string
  default = "db.t4g.medium"
}
variable "serverless_min_ncu" {
  type        = number
  default     = 0
  description = "above zero (for example 1) uses db.serverless with this minimum instead of instance_class"
}
variable "serverless_max_ncu" {
  type    = number
  default = 8
}
variable "engine_version" {
  type        = string
  default     = null
  description = "null takes the current default engine version"
}
variable "parameter_group_family" {
  type    = string
  default = "neptune1.4"
}
variable "deletion_protection" {
  type    = bool
  default = false
}
variable "tags" {
  type    = map(string)
  default = {}
}

locals {
  serverless = var.serverless_min_ncu > 0
}

resource "aws_neptune_subnet_group" "this" {
  name       = var.name
  subnet_ids = var.private_subnet_ids
  tags       = var.tags
}

resource "aws_security_group" "neptune" {
  name        = "${var.name}-neptune"
  description = "Neptune: 8182 from its clients only"
  vpc_id      = var.vpc_id
  tags        = var.tags
}

# A group for clients created after this module (the graph tools' Lambda): attach it to reach Neptune.
resource "aws_security_group" "client" {
  name        = "${var.name}-neptune-client"
  description = "Neptune clients: out to Neptune on 8182 and to S3 through the VPC endpoint"
  vpc_id      = var.vpc_id
  tags        = var.tags
}

resource "aws_vpc_security_group_egress_rule" "client_to_neptune" {
  security_group_id            = aws_security_group.client.id
  referenced_security_group_id = aws_security_group.neptune.id
  from_port                    = 8182
  to_port                      = 8182
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "client_https" {
  security_group_id = aws_security_group.client.id
  cidr_ipv4         = "0.0.0.0/0"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  description       = "S3 through the gateway endpoint (the private subnets have no other route out)"
}

resource "aws_vpc_security_group_ingress_rule" "client" {
  security_group_id            = aws_security_group.neptune.id
  referenced_security_group_id = aws_security_group.client.id
  from_port                    = 8182
  to_port                      = 8182
  ip_protocol                  = "tcp"
  description                  = "client"
}

resource "aws_vpc_security_group_ingress_rule" "clients" {
  for_each                     = var.client_security_group_ids
  security_group_id            = aws_security_group.neptune.id
  referenced_security_group_id = each.value
  from_port                    = 8182
  to_port                      = 8182
  ip_protocol                  = "tcp"
  description                  = each.key
}

resource "aws_neptune_cluster_parameter_group" "this" {
  name   = var.name
  family = var.parameter_group_family
  parameter {
    name  = "neptune_enable_audit_log"
    value = "1"
  }
  parameter {
    name  = "neptune_query_timeout"
    value = "30000"
  }
  tags = var.tags
}

resource "aws_neptune_cluster" "this" {
  cluster_identifier                   = var.name
  engine                               = "neptune"
  engine_version                       = var.engine_version
  neptune_subnet_group_name            = aws_neptune_subnet_group.this.name
  vpc_security_group_ids               = [aws_security_group.neptune.id]
  neptune_cluster_parameter_group_name = aws_neptune_cluster_parameter_group.this.name
  iam_database_authentication_enabled  = true
  storage_encrypted                    = true
  backup_retention_period              = 1
  preferred_backup_window              = "03:00-04:00"
  skip_final_snapshot                  = true
  deletion_protection                  = var.deletion_protection
  apply_immediately                    = true
  enable_cloudwatch_logs_exports       = ["audit"]

  dynamic "serverless_v2_scaling_configuration" {
    for_each = local.serverless ? [1] : []
    content {
      min_capacity = var.serverless_min_ncu
      max_capacity = var.serverless_max_ncu
    }
  }
  tags = var.tags
}

resource "aws_neptune_cluster_instance" "primary" {
  identifier                 = "${var.name}-1"
  cluster_identifier         = aws_neptune_cluster.this.id
  engine                     = "neptune"
  instance_class             = local.serverless ? "db.serverless" : var.instance_class
  neptune_subnet_group_name  = aws_neptune_subnet_group.this.name
  apply_immediately          = true
  auto_minor_version_upgrade = true
  tags                       = var.tags
}

data "aws_region" "current" {}
data "aws_caller_identity" "me" {}

locals {
  # neptune-db:* actions are granted on arn:aws:neptune-db:<region>:<account>:<cluster resource id>/*
  data_arn = "arn:aws:neptune-db:${data.aws_region.current.region}:${data.aws_caller_identity.me.account_id}:${aws_neptune_cluster.this.cluster_resource_id}/*"
}

output "endpoint" { value = aws_neptune_cluster.this.endpoint }
output "reader_endpoint" { value = aws_neptune_cluster.this.reader_endpoint }
output "port" { value = aws_neptune_cluster.this.port }
output "cluster_id" { value = aws_neptune_cluster.this.id }
output "security_group_id" { value = aws_security_group.neptune.id }
output "client_security_group_id" { value = aws_security_group.client.id }
output "data_arn" {
  value       = local.data_arn
  description = "the resource for neptune-db:ReadDataViaQuery, WriteDataViaQuery and DeleteDataViaQuery"
}
