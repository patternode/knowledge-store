# The same outputs as the reference root, so its tools (examples/agent/invoke.py --stack-dir) work here.
output "portal_url" { value = module.knowledge_store.portal_url }
output "lake_bucket" { value = module.knowledge_store.lake_bucket }
output "upload_to" { value = module.knowledge_store.upload_to }
output "image_build_project" { value = module.knowledge_store.image_build_project }
output "run_now" { value = module.knowledge_store.run_now }
output "pipeline_logs" { value = module.knowledge_store.pipeline_logs }
output "cognito_user_pool" { value = module.knowledge_store.cognito_user_pool }
output "agent" { value = module.knowledge_store.agent }
output "provided_ontologies" { value = module.knowledge_store.provided_ontologies }
