terraform {
  required_version = ">= 1.6.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.40"
    }
  }
}

provider "digitalocean" {
  token = var.do_token
}

# 1. Carica la chiave SSH su DigitalOcean
resource "digitalocean_ssh_key" "default" {
  name       = "chiave-corso-devops"
  public_key = var.ssh_public_key
}

# 2. Prepara lo script cloud-init con i nostri valori
locals {
  user_data = templatefile("${path.module}/cloud-init.yaml", {
    docker_image = var.docker_image
  })
}

# 3. Crea il server (Droplet)
resource "digitalocean_droplet" "todo" {
  name      = "todo-app"
  image     = "ubuntu-24-04-x64"
  region    = var.region
  size      = var.droplet_size
  ssh_keys  = [digitalocean_ssh_key.default.id]
  user_data = local.user_data
  tags      = ["corso-devops", "todo-app"]
}

# 4. Crea un firewall sul cloud (livello extra di sicurezza)
resource "digitalocean_firewall" "todo" {
  name        = "todo-app-fw"
  droplet_ids = [digitalocean_droplet.todo.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

data "digitalocean_project" "corso" {
  name = "devops-course"  # ← metti il nome ESATTO come compare nel pannello
}

resource "digitalocean_project_resources" "corso" {
  project   = data.digitalocean_project.corso.id
  resources = [digitalocean_droplet.todo.urn]
}