# The pipeline: the same image as on AWS, built by ACR Tasks in this subscription from this
# repository's source, run as Container Apps jobs.
#
#   uploads   an event-triggered job: KEDA watches the uploads queue (as the pipeline identity,
#             no keys) and starts a run when it has messages. The run empties the queue, then
#             sweeps; the sweep reads the lake, so the messages are only a signal.
#   schedule  the safety-net sweep, on schedule_cron
#
# Two runs at once are harmless: the sweep's lock (a conditional write in the lake) lets one work.

resource "azurerm_container_registry" "this" {
  name                          = "cr${local.short}"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.this.name
  sku                           = "Basic"
  admin_enabled                 = false
  anonymous_pull_enabled        = false
  public_network_access_enabled = true
  tags                          = local.tags
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.this.id
  role_definition_name = "AcrPull"
  principal_id         = local.id["pipeline"].principal_id
}

data "archive_file" "pipeline_src" {
  type        = "zip"
  source_dir  = "${local.repo_root}/src"
  output_path = "${path.root}/.build/pipeline-src.zip"
  excludes    = ["**/__pycache__/**", "**/*.pyc", "*.egg-info/**"]
}

locals {
  image_tag = substr(sha256(join("", [
    data.archive_file.pipeline_src.output_sha256,
    filesha256("${local.repo_root}/Dockerfile"),
    filesha256("${local.repo_root}/pyproject.toml"),
  ])), 0, 16)
  image = "${azurerm_container_registry.this.login_server}/pipeline:${local.image_tag}"
}

# ACR Tasks builds the image in Azure from the repository's source (the context honours
# .dockerignore). Needs the Azure CLI, signed in to the same subscription, where Terraform runs.
resource "terraform_data" "image" {
  triggers_replace = [local.image_tag, azurerm_container_registry.this.id]
  provisioner "local-exec" {
    working_dir = local.repo_root
    command     = "az acr build --subscription ${data.azurerm_client_config.me.subscription_id} --registry ${azurerm_container_registry.this.name} --image pipeline:${local.image_tag} --build-arg EXTRAS=azure,mongo,neo4j,age --file Dockerfile ."
  }
}

resource "azurerm_container_app_environment" "this" {
  name                       = "cae-${var.name}"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.this.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  tags                       = local.tags
}

locals {
  pipeline_env = merge(local.common_env, {
    AZURE_CLIENT_ID     = local.id["pipeline"].client_id
    EXTRACTION_MODEL_ID = var.foundry.extraction_model
    LEDGER_JOB          = "sweep"
    }, local.graph_backend == "age" ? {
    AGE_DSN     = "host=${azurerm_postgresql_flexible_server.age[0].fqdn} port=5432 dbname=postgres user=${local.id["pipeline"].name} sslmode=require"
    AGE_READERS = local.id["api"].name
  } : {})
  pipeline_secrets = merge(
    { MONGODB_URI = { name = "mongodb-uri", id = azurerm_key_vault_secret.mongodb_uri.versionless_id } },
    local.graph_backend == "neo4j" ? { NEO4J_PASSWORD = { name = "neo4j-password", id = azurerm_key_vault_secret.neo4j_password[0].versionless_id } } : {},
  )
  jobs = {
    uploads  = { env = { LAKE_QUEUE_URL = azurerm_storage_account.lake.primary_queue_endpoint, UPLOAD_QUEUE = "uploads" } }
    schedule = { env = {} }
  }
}

resource "azurerm_container_app_job" "sweep" {
  for_each                     = { for k, v in local.jobs : k => v if k != "schedule" || var.schedule_enabled }
  name                         = "${var.name}-${each.key}"
  location                     = var.location
  resource_group_name          = azurerm_resource_group.this.name
  container_app_environment_id = azurerm_container_app_environment.this.id
  replica_timeout_in_seconds   = 6 * 3600 # the sweep lock's TTL
  replica_retry_limit          = 0        # the next trigger or the schedule retries; the sweep is idempotent

  identity {
    type         = "UserAssigned"
    identity_ids = [local.id["pipeline"].id]
  }
  registry {
    server   = azurerm_container_registry.this.login_server
    identity = local.id["pipeline"].id
  }
  dynamic "secret" {
    for_each = local.pipeline_secrets
    content {
      name                = secret.value.name
      key_vault_secret_id = secret.value.id
      identity            = local.id["pipeline"].id
    }
  }

  dynamic "event_trigger_config" {
    for_each = each.key == "uploads" ? [1] : []
    content {
      parallelism              = 1
      replica_completion_count = 1
      scale {
        min_executions              = 0
        max_executions              = 1
        polling_interval_in_seconds = 30
        rules {
          name             = "uploads"
          custom_rule_type = "azure-queue"
          identity_id      = local.id["pipeline"].id
          metadata = {
            accountName = azurerm_storage_account.lake.name
            queueName   = azurerm_storage_queue.this["uploads"].name
            queueLength = "1"
          }
        }
      }
    }
  }
  dynamic "schedule_trigger_config" {
    for_each = each.key == "schedule" ? [1] : []
    content {
      cron_expression          = var.schedule_cron
      parallelism              = 1
      replica_completion_count = 1
    }
  }

  template {
    container {
      name   = "sweep"
      image  = local.image
      cpu    = 2
      memory = "4Gi"
      dynamic "env" {
        for_each = merge(local.pipeline_env, each.value.env)
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "env" {
        for_each = local.pipeline_secrets
        content {
          name        = env.key
          secret_name = env.value.name
        }
      }
    }
  }

  tags       = local.tags
  depends_on = [terraform_data.image, azurerm_role_assignment.acr_pull, azurerm_role_assignment.secrets, azurerm_role_assignment.lake]
}
