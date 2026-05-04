# ============================================================================
# database-mysql.tf
# Managed MySQL su DigitalOcean.
#
# CONTESTO PEDAGOGICO (lezione DB managed):
# - Un database self-managed e' un single-point-of-failure: niente backup
#   automatici, niente point-in-time recovery, niente HA.
# - Il managed MySQL di DigitalOcean offre snapshot giornalieri, PITR,
#   patch automatiche, e (con node_count >= 2) failover automatico.
# - Stessa lezione del Valkey: alcune cose si comprano, non si gestiscono.
#
# TLS OBBLIGATORIA: il cluster e' raggiungibile solo via TLS. Il driver
# (PyMySQL) riceve un certificato CA che Terraform espone come output
# sensibile (vedi outputs.tf -> mysql_ca_certificate).
# ============================================================================

resource "digitalocean_database_cluster" "mysql" {
  # name: come appare nel pannello DO -> Databases
  name = "${var.name_prefix}-mysql"

  # engine: "mysql" - distinto da "valkey" usato per la cache
  engine = "mysql"

  # version: major MySQL (8 = unica versione managed disponibile su DO oggi)
  version = var.mysql_engine_version

  # size: slug della taglia del cluster
  # db-s-1vcpu-1gb = ~$15/mese, basic tier (sufficiente per la lezione)
  size = var.mysql_size

  # region: stessa dei nodi app per latenza minima
  region = var.region

  # node_count: 1 = nodo singolo (no HA, ma cheap)
  # Per produzione: 2+ per failover automatico (e snapshot leggermente piu' fitti)
  node_count = var.mysql_node_count

  # private_network_uuid: collega il cluster alla nostra VPC.
  # I nodi app lo raggiungono via hostname privato (.b.db.ondigitalocean.com)
  private_network_uuid = digitalocean_vpc.main.id

  tags = local.common_tags
}

# Database applicativo dentro al cluster.
# Un cluster puo' ospitare N database; ne creiamo uno dedicato all'app.
resource "digitalocean_database_db" "app" {
  cluster_id = digitalocean_database_cluster.mysql.id
  name       = var.mysql_database_name
}

# Utente applicativo. La password viene generata da DO al create.
resource "digitalocean_database_user" "app" {
  cluster_id = digitalocean_database_cluster.mysql.id
  name       = var.mysql_user_name

  # mysql_auth_plugin: caching_sha2_password e' il default di MySQL 8.
  # PyMySQL >= 1.1 lo supporta nativamente quando la connessione e' su TLS
  # (lo e' sempre con DO managed). Niente bisogno della libreria 'cryptography'.
  # NB: il provider accetta i valori coi underscore (non i trattini).
  mysql_auth_plugin = "caching_sha2_password"
}

# Data source per leggere il CA certificate del cluster.
# Sul provider DigitalOcean attuale, ca_certificate non e' un attributo del
# cluster ma una resource separata interrogabile via data source.
data "digitalocean_database_ca" "mysql" {
  cluster_id = digitalocean_database_cluster.mysql.id
}

# Firewall del cluster: solo le Droplet con tag "devops-course" possono
# connettersi (stesso pattern del Valkey - vedi database-valkey.tf).
resource "digitalocean_database_firewall" "mysql_fw" {
  cluster_id = digitalocean_database_cluster.mysql.id

  rule {
    type  = "tag"
    value = "devops-course"
  }
}
