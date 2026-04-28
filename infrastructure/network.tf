# ============================================================================
# network.tf
# VPC privata: rete interna dove i nodi si parlano via IP privati.
# ============================================================================

resource "digitalocean_vpc" "main" {
  name   = "${var.name_prefix}-vpc"
  region = var.region

  # ip_range: subnet della VPC in notazione CIDR.
  # 10.10.10.0/24 = 256 IP privati (10.10.10.0 → 10.10.10.255)
  # /24 = primi 24 bit "rete", ultimi 8 "host"
  ip_range = "10.10.10.0/24"
}