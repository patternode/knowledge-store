output "portal_url" {
  value = module.knowledge_store.portal_url
}

output "upload_to" {
  value = module.knowledge_store.upload_to
}

output "lake_uri" {
  value = module.knowledge_store.lake_uri
}

output "mcp_url" {
  value = module.knowledge_store.mcp_url
}

output "entra" {
  value = module.knowledge_store.entra
}

output "copilot_client_secret" {
  value     = module.knowledge_store.copilot_client_secret
  sensitive = true
}

output "resource_group" {
  value = module.knowledge_store.resource_group
}

output "graph_backend" {
  value = module.knowledge_store.graph_backend
}
