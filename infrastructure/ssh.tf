# ============================================================================
# ssh.tf
# Carica la chiave SSH pubblica su DigitalOcean.
# Verr`a iniettata in /root/.ssh/authorized_keys di tutte le Droplet.
# ============================================================================

resource "digitalocean_ssh_key" "default" {
  # name: come la chiave appare nel pannello DO -> Settings -> Security
  # "${var.x}" = interpolazione di variabile dentro stringa
  name = "${var.name_prefix}-key"

  # public_key: contenuto della chiave pubblica (da terraform.tfvars)
  public_key = var.ssh_public_key
}