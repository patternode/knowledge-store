output "portal_url" { value = module.portal.url }
output "lake_bucket" { value = module.lake.bucket }
output "upload_to" {
  value       = { for id, c in local.collections : id => "s3://${module.lake.bucket}/landing/${id}/" }
  description = "where each collection's uploads go (for collections with the default source); folders are kept as metadata"
}
output "image_build_project" {
  value       = module.build.codebuild_project
  description = "the first image build starts on apply; watch it in CodeBuild before the first run"
}
output "run_now" {
  description = "start a sweep by hand (the uploads and the schedule start it on their own)"
  value = join(" ", [
    "aws ecs run-task --cluster ${module.pipeline.cluster_name} --task-definition ${module.pipeline.task_definition}",
    "--launch-type FARGATE --network-configuration",
    "'awsvpcConfiguration={subnets=[${join(",", module.network.public_subnet_ids)}],securityGroups=[${module.pipeline.security_group_id}],assignPublicIp=ENABLED}'",
  ])
}
output "pipeline_logs" { value = module.pipeline.log_group }
output "cognito_user_pool" { value = module.identity.user_pool_id }
output "cognito_client_id" { value = module.identity.client_id }
output "agent" {
  description = "the chat agent: its runtime (empty until agent.runtime = true), Gateway and guardrail"
  value = {
    runtime_arn   = module.agent.runtime_arn
    qualifier     = module.agent.runtime_qualifier
    gateway_url   = module.agent.gateway_url
    guardrail_id  = module.agent.guardrail_id
    image_project = module.build.agent_codebuild_project
  }
}

output "knowledge_graph" {
  description = "the Neptune cluster the sweep loads and the graph tools query (null when off)"
  value       = var.knowledge_graph.enabled ? { endpoint = module.knowledge_graph[0].endpoint, port = module.knowledge_graph[0].port } : null
}

output "knowledge_base" {
  description = "the passages' Knowledge Base (null when off)"
  value       = var.knowledge_base.enabled ? { id = module.knowledge_base[0].knowledge_base_id, data_source_id = module.knowledge_base[0].data_source_id } : null
}

output "evaluate" {
  description = "run an evaluation set against the deployed chat, as a signed-in person (see README)"
  value       = "python -m knowledge_store.evals <set.yaml> --api ${trimsuffix(module.portal.url, "/")} --token-env KS_TOKEN --yes"
}

output "provided_ontologies" {
  description = "collections that bring their own ontology, with the files uploaded for each (the rest discover theirs)"
  value = { for id in distinct([for k in keys(local.ontology_files) : split("/", k)[0]]) :
    id => sort([for k in keys(local.ontology_files) : split("/", k)[1] if split("/", k)[0] == id])
  }
}
