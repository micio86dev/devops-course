# ============================================================================
# null-resource-node-agents.tf
# Installa node_exporter, cAdvisor e Promtail su ciascun nodo app via SSH.
# Usa null_resource + remote-exec perché i nodi esistono già (cloud-init è
# già avvenuto). Rieseguito se cambia l'IP del nodo monitoring o dell'app node.
# ============================================================================

locals {
  app_nodes = {
    "app-1" = {
      public_ip  = digitalocean_droplet.app[0].ipv4_address
      private_ip = digitalocean_droplet.app[0].ipv4_address_private
    }
    "app-2" = {
      public_ip  = digitalocean_droplet.app[1].ipv4_address
      private_ip = digitalocean_droplet.app[1].ipv4_address_private
    }
  }
}

resource "null_resource" "node_agent" {
  for_each = local.app_nodes

  # Re-run se cambia l'IP del nodo monitoring (config Promtail) o del nodo stesso
  triggers = {
    monitoring_private_ip = digitalocean_droplet.monitoring.ipv4_address_private
    node_private_ip       = each.value.private_ip
  }

  connection {
    type        = "ssh"
    host        = each.value.public_ip
    user        = "root"
    private_key = file(pathexpand(var.ssh_private_key_path))
  }

  provisioner "remote-exec" {
    inline = [
      # Aspetta che cloud-init finisca (installa Docker — può richiedere 2-4 min)
      "cloud-init status --wait || true",
      "mkdir -p /root/monitoring",
    ]
  }

  provisioner "file" {
    content = templatefile("${path.module}/templates/promtail.yml.tpl", {
      monitoring_node_ip = digitalocean_droplet.monitoring.ipv4_address_private
      node_name          = each.key
    })
    destination = "/root/monitoring/promtail.yml"
  }

  provisioner "file" {
    source      = "${path.module}/templates/agents-compose.yml"
    destination = "/root/monitoring/docker-compose.agents.yml"
  }

  provisioner "remote-exec" {
    inline = [
      # Installa Docker se cloud-init non l'ha fatto (idempotente)
      "command -v docker >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y docker.io docker-compose-v2 && systemctl enable --now docker)",
      "systemctl is-active --quiet docker || systemctl start docker",
      "cd /root/monitoring && docker compose -f docker-compose.agents.yml up -d",
      # Scrivi l'endpoint OTLP nel file env dell'app (sourciato dal CI/CD deploy)
      "mkdir -p /root/docker-todo",
      "echo 'OTLP_ENDPOINT=http://${digitalocean_droplet.monitoring.ipv4_address_private}:4317' > /root/docker-todo/.env.monitoring",
      "chmod 600 /root/docker-todo/.env.monitoring",
    ]
  }

  depends_on = [
    digitalocean_droplet.monitoring,
    digitalocean_firewall.monitoring,
    digitalocean_firewall.app,
  ]
}
