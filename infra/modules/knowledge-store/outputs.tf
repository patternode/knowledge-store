output "portal_url" { value = module.portal.url }
output "portal_distribution_id" {
  value       = module.portal.distribution_id
  description = "the portal's CloudFront distribution, for subscribing it to a pricing plan in the console"
}
output "portal_web_acl_arn" {
  value       = module.portal.web_acl_arn
  description = "the web ACL on the portal's distribution, or null when there is none"
}
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
output "agent" {
  description = "the example agent: how to call it (see examples/agent/invoke.py)"
  value = var.agent.enabled ? {
    gateway_url    = module.agent[0].gateway_url
    runtime_arn    = module.agent[0].runtime_arn
    caller_client  = module.identity.machine_client_ids["caller"]
    token_endpoint = module.identity.token_endpoint
    scope_prefix   = module.identity.scope_prefix
    image_project  = module.build.agent_codebuild_project
  } : null
}
