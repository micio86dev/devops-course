# ============================================================================
# droplet-db.tf
# Droplet del nodo DB: serve la share NFS con il file SQLite.
# ============================================================================

resource "digitalocean_droplet" "db" {
  name = "${var.name_prefix}-db"

  # image: slug dell'immagine OS
  # Lista completa: doctl compute image list-distribution --public
  image = "ubuntu-24-04-x64"

  region = var.region
  size   = var.droplet_size

  # vpc_uuid: aggancia la Droplet alla VPC.
  # Riferimento incrociato: legge la VPC definita in network.tf
  vpc_uuid = digitalocean_vpc.main.id

  # ssh_keys: lista di ID di chiavi da iniettare in authorized_keys
  ssh_keys = [digitalocean_ssh_key.default.id]

  # user_data: script cloud-init eseguito al primo boot.
  # file(): legge il contenuto del file e lo passa come stringa.
  # path.module = path della cartella corrente
  user_data = file("${path.module}/cloud-init/db.yaml")

  # tags: lista di tag (per filtri nel pannello, billing, ecc.)
  tags = local.common_tags
}