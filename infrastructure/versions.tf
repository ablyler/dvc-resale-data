terraform {
  required_version = ">= 1.8.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }

    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
    }

    random = {
      source  = "hashicorp/random"
      version = "~> 3.7"
    }
  }

  backend "azurerm" {
    # Backend configuration will be provided via CLI or environment variables
    resource_group_name  = "dvc-resale-data"
    storage_account_name = "dvcresaledatatfstate"
    container_name       = "tfstate"
    key                  = "terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }



    cognitive_account {
      purge_soft_delete_on_destroy = true
    }
  }

  subscription_id = var.subscription_id
}

provider "azuread" {
  # No additional configuration required
}

provider "random" {
  # No additional configuration required
}
