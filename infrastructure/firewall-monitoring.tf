# ============================================================================
# firewall-monitoring.tf
# Firewall per il nodo monitoring:
# - SSH (22) dall'esterno per debug
# - HTTP (80) dall'esterno per Grafana via nginx
# - Loki push (3100) SOLO dalla VPC (Promtail sui nodi app)
# - Outbound aperto (per docker pull, apt, scraping esportatori)
# ============================================================================

resource "digitalocean_firewall" "monitoring" {
  name        = "${var.name_prefix}-monitoring-fw"
  droplet_ids = [digitalocean_droplet.monitoring.id]
  tags        = local.common_tags

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Grafana via nginx — accesso pubblico
  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Loki push da Promtail sui nodi app (solo VPC privata)
  inbound_rule {
    protocol         = "tcp"
    port_range       = "3100"
    source_addresses = [digitalocean_vpc.main.ip_range]
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
