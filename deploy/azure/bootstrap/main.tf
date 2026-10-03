# Once per subscription: the storage account that holds the stack's Terraform state. Local state here.
#
#   az login
#   terraform init && terraform apply -var subscription_id=<subscription id>
#   terraform output -raw backend_hcl > ../stack/backend.hcl
#
# State is read and written with Entra ID (the account has no keys), so whoever applies the stack
# needs Storage Blob Data Contributor on the container; this grants it to whoever runs it.

terraform {
  required_version = ">= 1.10.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.40" }
    random  = { source = "hashicorp/random", version = "~> 3.7" }
  }
}

variable "subscription_id" { type = string }
variable "location" {
  type    = string
  default = "eastus2"
}
variable "name" {
  type    = string
  default = "knowledge-store"
}

provider "azurerm" {
  subscription_id     = var.subscription_id
  storage_use_azuread = true
  features {}
}

data "azurerm_client_config" "me" {}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

resource "azurerm_resource_group" "state" {
  name     = "rg-${var.name}-tfstate"
  location = var.location
}

resource "azurerm_storage_account" "state" {
  name                            = "st${substr(replace(var.name, "-", ""), 0, 12)}${random_string.suffix.result}tf"
  resource_group_name             = azurerm_resource_group.state.name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "ZRS"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  blob_properties {
    versioning_enabled = true # every state version is kept, so a bad apply can be rolled back
    delete_retention_policy {
      days = 30
    }
  }
}

resource "azurerm_storage_container" "state" {
  name               = "tfstate"
  storage_account_id = azurerm_storage_account.state.id
}

resource "azurerm_role_assignment" "me" {
  scope                = azurerm_storage_container.state.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.me.object_id
}

output "backend_hcl" {
  value = <<-EOT
    resource_group_name  = "${azurerm_resource_group.state.name}"
    storage_account_name = "${azurerm_storage_account.state.name}"
    container_name       = "${azurerm_storage_container.state.name}"
  EOT
}
