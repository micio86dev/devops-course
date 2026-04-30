# ============================================================================
# provider.tf
# Configura Terraform e dichiara i provider da scaricare.
# ============================================================================

terraform {
  # required_version: rifiuta versioni troppo vecchie
  # >= 1.6.0 per features moderne
  required_version = ">= 1.6.0"

  # required_providers: dichiara da dove scaricare i provider
  required_providers {
    digitalocean = {
      # source: namespace del provider sul Terraform Registry
      source = "digitalocean/digitalocean"
      # version: pin. ~> 2.40 = "2.40 o superiore, ma non 3.x"
      # Evita rotture quando esce una nuova major version
      version = "~> 2.40"
    }
  }
}

# Configura come Terraform parla con DigitalOcean
provider "digitalocean" {
  # var.do_token: riferimento alla variabile in variables.tf
  # MAI hardcodare il token qui!
  token = var.do_token
}