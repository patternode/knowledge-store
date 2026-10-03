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
}
