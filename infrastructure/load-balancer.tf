# ============================================================================
# load-balancer.tf
# Load Balancer pubblico: smista il traffico tra i 2 nodi app.
# ============================================================================

resource "digitalocean_loadbalancer" "public" {
  name   = "${var.name_prefix}-lb"
  region = var.region

  # vpc_uuid: anche il LB sta nella VPC, parla con i nodi via IP privato
  vpc_uuid = digitalocean_vpc.main.id

  # forwarding_rule: come instradare il traffico in entrata
  forwarding_rule {
    # entry_*: cosa il LB accetta DALL'ESTERNO
    entry_port     = 80 # browser → http://<lb-ip>/
    entry_protocol = "http"

    # target_*: dove inoltra ai nodi app
    target_port     = var.host_port # 5001 (porta esterna delle Droplet)
    target_protocol = "http"
    # Nota: NON 80 sulle Droplet, ma 5001 — perché Docker espone su 5001
  }

  # healthcheck: il LB testa periodicamente i nodi
  healthcheck {
    port                     = var.host_port # controlla la 5001
    protocol                 = "http"
    path                     = "/" # endpoint da chiamare
    check_interval_seconds   = 10  # ogni 10 secondi
    response_timeout_seconds = 5   # max 5s di attesa
    unhealthy_threshold      = 3   # 3 fail consecutivi → "down"
    healthy_threshold        = 2   # 2 success consecutivi → "up"
  }

  # droplet_ids: a quali nodi inoltrare il traffico
  # [*] = splat operator: prendi l'attributo da TUTTI gli elementi del count.
  # digitalocean_droplet.app[*].id → [id_app1, id_app2]
  droplet_ids = digitalocean_droplet.app[*].id
}