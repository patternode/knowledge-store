# The same outputs as the reference root.
output "portal_url" { value = module.knowledge_store.portal_url }
output "portal_cloudfront_domain" { value = module.knowledge_store.portal_cloudfront_domain }
output "lake_bucket" { value = module.knowledge_store.lake_bucket }
output "upload_to" { value = module.knowledge_store.upload_to }
output "image_build_project" { value = module.knowledge_store.image_build_project }
output "run_now" { value = module.knowledge_store.run_now }
output "pipeline_logs" { value = module.knowledge_store.pipeline_logs }
output "cognito_user_pool" { value = module.knowledge_store.cognito_user_pool }
output "cognito_client_id" { value = module.knowledge_store.cognito_client_id }
output "agent" { value = module.knowledge_store.agent }
output "knowledge_graph" { value = module.knowledge_store.knowledge_graph }
output "knowledge_base" { value = module.knowledge_store.knowledge_base }
output "evaluate" { value = module.knowledge_store.evaluate }
output "provided_ontologies" { value = module.knowledge_store.provided_ontologies }
output "sign_in" { value = module.knowledge_store.sign_in }
