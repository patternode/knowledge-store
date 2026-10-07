output "portal_url" { value = module.knowledge_store.portal_url }
output "portal_cloudfront_domain" { value = module.knowledge_store.portal_cloudfront_domain }
output "lake_bucket" { value = module.knowledge_store.lake_bucket }
output "upload_to" {
  value       = module.knowledge_store.upload_to
  description = "where each collection's uploads go (for collections with the default source); folders are kept as metadata"
}
output "image_build_project" {
  value       = module.knowledge_store.image_build_project
  description = "the first image build starts on apply; watch it in CodeBuild before the first run"
}
output "run_now" {
  value       = module.knowledge_store.run_now
  description = "start a sweep by hand (the uploads and the schedule start it on their own)"
}
output "pipeline_logs" { value = module.knowledge_store.pipeline_logs }
output "cognito_user_pool" { value = module.knowledge_store.cognito_user_pool }
output "cognito_client_id" { value = module.knowledge_store.cognito_client_id }
output "agent" {
  value       = module.knowledge_store.agent
  description = "the chat agent: its runtime (empty until agent.runtime = true), Gateway and guardrail"
}
output "knowledge_graph" { value = module.knowledge_store.knowledge_graph }
output "knowledge_base" { value = module.knowledge_store.knowledge_base }
output "evaluate" {
  value       = module.knowledge_store.evaluate
  description = "run an evaluation set against the deployed chat, as a signed-in person"
}

output "provided_ontologies" {
  value       = module.knowledge_store.provided_ontologies
  description = "collections that bring their own ontology, and the files uploaded for each"
}
output "sign_in" { value = module.knowledge_store.sign_in }
