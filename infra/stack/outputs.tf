output "portal_url" { value = module.knowledge_store.portal_url }
output "portal_distribution_id" {
  value       = module.knowledge_store.portal_distribution_id
  description = "the portal's CloudFront distribution, for subscribing it to a pricing plan in the console"
}
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
output "agent" {
  value       = module.knowledge_store.agent
  description = "the example agent: how to call it (see examples/agent/invoke.py)"
}
