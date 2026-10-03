# The lake: one container, layered by prefix as on S3, with versioning and soft delete. Uploads
# under landing/ raise BlobCreated events, which Event Grid delivers to the uploads queue; the
# queue starts the pipeline job (pipeline.tf). The chat queue carries questions to the chat worker.

resource "azurerm_storage_account" "lake" {
  name                            = "st${local.short}lake"
  location                        = var.location
  resource_group_name             = azurerm_resource_group.this.name
  account_tier                    = "Standard"
  account_replication_type        = "ZRS"
  account_kind                    = "StorageV2"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 14
    }
    container_delete_retention_policy {
      days = 14
    }
  }
  tags = local.tags
}

resource "azurerm_storage_container" "lake" {
  name               = "lake"
  storage_account_id = azurerm_storage_account.lake.id
}

resource "azurerm_storage_container" "deadletter" {
  name               = "deadletter"
  storage_account_id = azurerm_storage_account.lake.id
}

resource "azurerm_storage_queue" "this" {
  for_each           = toset(["uploads", "chat"])
  name               = each.key
  storage_account_id = azurerm_storage_account.lake.id
}

# Old versions of overwritten objects go after 30 days; landing/ is the uploader's to manage.
resource "azurerm_storage_management_policy" "lake" {
  storage_account_id = azurerm_storage_account.lake.id
  rule {
    name    = "expire-old-versions"
    enabled = true
    filters {
      blob_types = ["blockBlob"]
    }
    actions {
      version {
        delete_after_days_since_creation = 30
      }
    }
  }
}

resource "azurerm_role_assignment" "lake" {
  for_each = {
    pipeline_blobs = { id = "pipeline", role = "Storage Blob Data Contributor" }
    pipeline_queue = { id = "pipeline", role = "Storage Queue Data Message Processor" }
    api_blobs      = { id = "api", role = "Storage Blob Data Reader" }
    api_queue      = { id = "api", role = "Storage Queue Data Contributor" }
    events_queue   = { id = "events", role = "Storage Queue Data Message Sender" }
    events_dead    = { id = "events", role = "Storage Blob Data Contributor" }
  }
  scope                = azurerm_storage_account.lake.id
  role_definition_name = each.value.role
  principal_id         = local.id[each.value.id].principal_id
}

# Curators upload to landing/ with their own sign-in (az storage blob upload --auth-mode login).
resource "azurerm_role_assignment" "uploaders" {
  for_each             = toset(var.admin_principal_ids)
  scope                = azurerm_storage_container.lake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = each.value
}

resource "azurerm_eventgrid_system_topic" "lake" {
  name                = "evgt-${var.name}-lake"
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  source_resource_id  = azurerm_storage_account.lake.id
  topic_type          = "Microsoft.Storage.StorageAccounts"
  identity {
    type         = "UserAssigned"
    identity_ids = [local.id["events"].id]
  }
  tags = local.tags
}

resource "azurerm_eventgrid_system_topic_event_subscription" "uploads" {
  name                 = "uploads"
  system_topic         = azurerm_eventgrid_system_topic.lake.name
  resource_group_name  = azurerm_resource_group.this.name
  included_event_types = ["Microsoft.Storage.BlobCreated"]
  subject_filter {
    subject_begins_with = "/blobServices/default/containers/${azurerm_storage_container.lake.name}/blobs/landing/"
  }
  storage_queue_endpoint {
    storage_account_id                    = azurerm_storage_account.lake.id
    queue_name                            = azurerm_storage_queue.this["uploads"].name
    queue_message_time_to_live_in_seconds = 604800
  }
  delivery_identity {
    type                   = "UserAssigned"
    user_assigned_identity = local.id["events"].id
  }
  dead_letter_identity {
    type                   = "UserAssigned"
    user_assigned_identity = local.id["events"].id
  }
  storage_blob_dead_letter_destination {
    storage_account_id          = azurerm_storage_account.lake.id
    storage_blob_container_name = azurerm_storage_container.deadletter.name
  }
  depends_on = [azurerm_role_assignment.lake]
}

# The collections and each one's sources, profile and settings, as the pipeline reads them.
locals {
  config_files = merge([for id, c in local.collections : {
    "${id}/sources"  = c.sources
    "${id}/profile"  = c.profile
    "${id}/settings" = c.settings
  }]...)
}

resource "azurerm_storage_blob" "collections" {
  name                 = "config/collections.json"
  storage_container_id = azurerm_storage_container.lake.id
  type                 = "Block"
  content_type         = "application/json"
  source_content       = jsonencode([for id in sort(keys(var.collections)) : { id = id }])
  depends_on           = [time_sleep.deployer_roles]
}

resource "azurerm_storage_blob" "collection_config" {
  for_each             = local.config_files
  name                 = "collections/${split("/", each.key)[0]}/config/${split("/", each.key)[1]}.json"
  storage_container_id = azurerm_storage_container.lake.id
  type                 = "Block"
  content_type         = "application/json"
  source_content       = jsonencode(each.value)
  depends_on           = [time_sleep.deployer_roles]
}

# The lake is the record. A delete lock stops a destroy, or a slip in the portal, from taking it;
# force_destroy_lake = true removes the lock.
resource "azurerm_management_lock" "lake" {
  count      = var.force_destroy_lake ? 0 : 1
  name       = "keep-the-lake"
  scope      = azurerm_storage_account.lake.id
  lock_level = "CanNotDelete"
  notes      = "The lake holds the record. Set force_destroy_lake = true to remove this lock."
}
