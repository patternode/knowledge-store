# The reference root: the Knowledge Store module with this directory's provider and backend.
# The launch stack and the quick start apply this. To deploy into your own infrastructure from a
# repository of your own, start from examples/deployment instead.
#
# After apply: upload files to s3://<lake>/landing/<collection>/ (outputs.upload_to). Once the agent
# image is built, set agent = { runtime = true } and apply again; then open the portal and ask.

module "knowledge_store" {
  source = "../modules/knowledge-store"

  admin_email                  = var.admin_email
  name                         = var.name
  collections                  = var.collections
  discovery                    = var.discovery
  extraction_workers           = var.extraction_workers
  schedule_expression          = var.schedule_expression
  schedule_enabled             = var.schedule_enabled
  llm_provider                 = var.llm_provider
  anthropic_api_key_secret_arn = var.anthropic_api_key_secret_arn
  extraction_model_id          = var.extraction_model_id
  chat_model_id                = var.chat_model_id
  portal_title                 = var.portal_title
  admin_private                = var.admin_private
  daily_questions              = var.daily_questions
  force_destroy_lake           = var.force_destroy_lake
  knowledge_graph              = var.knowledge_graph
  knowledge_base               = var.knowledge_base
  agent                        = var.agent
  guardrail                    = var.guardrail
  valves                       = var.valves
  budget                       = var.budget
}

# Before the module existed these were root modules; state from that layout moves on the next plan.
moved {
  from = module.lake
  to   = module.knowledge_store.module.lake
}
moved {
  from = module.build
  to   = module.knowledge_store.module.build
}
moved {
  from = module.network
  to   = module.knowledge_store.module.network
}
moved {
  from = module.pipeline
  to   = module.knowledge_store.module.pipeline
}
moved {
  from = module.identity
  to   = module.knowledge_store.module.identity
}
moved {
  from = module.portal
  to   = module.knowledge_store.module.portal
}
moved {
  from = module.agent
  to   = module.knowledge_store.module.agent
}
