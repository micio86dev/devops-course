# ============================================================================
# firewall-db.tf
# Firewall per il nodo DB:
# - SSH (22) dall'esterno per debug
# - NFS (2049) SOLO dai nodi della VPC
# ============================================================================

resource "digitalocean_firewall" "db" {
  name        = "${var.name_prefix}-db-fw"
  droplet_ids = [digitalocean_droplet.db.id]
  tags        = local.common_tags

  # SSH dall'esterno
  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # NFS (porta 2049) accessibile SOLO dai nodi nella VPC
  inbound_rule {
    protocol   = "tcp"
    port_range = "2049"
    # source_addresses: solo gli IP della nostra VPC.
    # digitalocean_vpc.main.ip_range = "10.10.10.0/24"
    # Nessun rischio che internet raggiunga il NFS.
    source_addresses = [digitalocean_vpc.main.ip_range]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}