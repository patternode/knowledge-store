terraform {
  required_version = ">= 1.10.0"

  required_providers {
    azurerm  = { source = "hashicorp/azurerm", version = "~> 4.40" }
    azuread  = { source = "hashicorp/azuread", version = "~> 3.4" }
    archive  = { source = "hashicorp/archive", version = "~> 2.7" }
    external = { source = "hashicorp/external", version = "~> 2.3" }
    random   = { source = "hashicorp/random", version = "~> 3.7" }
    time     = { source = "hashicorp/time", version = "~> 0.13" }
  }

  # Partial configuration: the storage account and container come from backend.hcl, which
  # ../bootstrap writes. State is read and written with Entra ID, not account keys.
  #   terraform init -backend-config=backend.hcl
  backend "azurerm" {
    key              = "knowledge-store.tfstate"
    use_azuread_auth = true
  }
}

# Credentials come from the Azure CLI (az login) or, in CI, from workload identity federation.
provider "azurerm" {
  subscription_id     = var.subscription_id
  storage_use_azuread = true # storage account keys are disabled everywhere
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
}

provider "azuread" {}
