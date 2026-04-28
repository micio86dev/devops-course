# ============================================================================
# firewall-redis.tf
# Firewall per il nodo Redis:
# - SSH (22) dall'esterno per debug
# - Redis (6379) SOLO dai nodi della VPC
# ============================================================================

resource "digitalocean_firewall" "redis" {
  name        = "${var.name_prefix}-redis-fw"
  droplet_ids = [digitalocean_droplet.redis.id]
  tags        = local.common_tags

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # Redis: porta 6379, solo VPC.
  # Stesso pattern del NFS — protezione di rete invece di password Redis.
  inbound_rule {
    protocol         = "tcp"
    port_range       = "6379"
    source_addresses = [digitalocean_vpc.main.ip_range]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}