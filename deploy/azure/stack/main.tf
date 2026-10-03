# The Azure reference root: the Knowledge Store module with this directory's provider and backend.
# See docs/architectures/azure-setup.md.
#
# After apply: upload files to landing/<collection>/ in the lake (outputs.upload_to) and open
# outputs.portal_url.

module "knowledge_store" {
  source = "../modules/knowledge-store"

  name                  = var.name
  location              = var.location
  admin_principal_ids   = var.admin_principal_ids
  publisher_email       = var.publisher_email
  tags                  = var.tags
  collections           = var.collections
  discovery             = var.discovery
  extraction_workers    = var.extraction_workers
  schedule_cron         = var.schedule_cron
  schedule_enabled      = var.schedule_enabled
  foundry               = var.foundry
  profile               = var.profile
  graph                 = var.graph
  document_projection   = var.document_projection
  mongodb_uri           = var.mongodb_uri
  neo4j                 = var.neo4j
  neo4j_password        = var.neo4j_password
  portal_title          = var.portal_title
  daily_questions       = var.daily_questions
  apim_sku              = var.apim_sku
  mcp_calls_per_minute  = var.mcp_calls_per_minute
  copilot_redirect_uris = var.copilot_redirect_uris
  force_destroy_lake    = var.force_destroy_lake
  python_command        = var.python_command
}
