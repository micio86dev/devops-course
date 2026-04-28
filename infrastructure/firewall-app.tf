# ============================================================================
# firewall-app.tf
# Firewall per i 2 nodi app:
# - SSH (22) dall'esterno per debug
# - HTTP (5001) SOLO dal Load Balancer
# - Outbound aperto (per docker pull, NFS, Redis)
# ============================================================================

resource "digitalocean_firewall" "app" {
  name = "${var.name_prefix}-app-fw"

  # droplet_ids: a quali Droplet applicare questo firewall
  droplet_ids = digitalocean_droplet.app[*].id

  tags = local.common_tags

  # === REGOLE INBOUND (chi può connettersi A queste Droplet) ===

  # SSH dall'esterno (per debug)
  inbound_rule {
    protocol   = "tcp"
    port_range = "22"
    # 0.0.0.0/0 = qualsiasi IPv4
    # ::/0      = qualsiasi IPv6
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # HTTP sulla 5001 SOLO dal Load Balancer
  inbound_rule {
    protocol = "tcp"
    # tostring(): converte numero → stringa (port_range vuole stringa!)
    port_range = tostring(var.host_port)

    # source_load_balancer_uids: regola SPECIALE di DO — accetta solo
    # se proviene dai LB elencati. Il pubblico NON può raggiungere :5001
    # direttamente, deve passare per il LB.
    source_load_balancer_uids = [digitalocean_loadbalancer.public.id]
  }

  # === REGOLE OUTBOUND (dove possono connettersi DA queste Droplet) ===

  # TCP outbound aperto: serve per docker pull, apt, NFS, Redis, ecc.
  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535" # tutte le porte TCP
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  # UDP outbound: serve principalmente per DNS (porta 53)
  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}