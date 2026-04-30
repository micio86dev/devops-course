# ============================================================================
# database-valkey.tf
# Managed Valkey su DigitalOcean: SOSTITUISCE la Droplet self-managed
# che prima girava redis-server da apt.
#
# CONTESTO STORICO (importante per la lezione):
# - Marzo 2024: Redis Ltd. cambia licenza (BSD -> SSPL/RSAL).
#   I cloud provider non possono piu' offrire Redis come servizio gestito.
# - La Linux Foundation lancia VALKEY: fork open-source di Redis 7.2.4
#   sotto BSD pulita, supportato da AWS, Google, Oracle, Ericsson, e DO.
# - 30 giugno 2025: DigitalOcean discontinua Managed Caching (Redis).
#   I cluster esistenti vengono migrati automaticamente a Valkey.
# - Oggi: l'unico engine cache disponibile su DO managed e' "valkey".
#
# COMPATIBILITA': Valkey e' wire-compatible con Redis.
# La nostra app Python con redis-py parla con Valkey senza modifiche al codice,
# usando una REDIS_URL = "rediss://default:PASSWORD@host:25061".
# Notare la doppia "s" in "rediss": Valkey su DO usa TLS obbligatoriamente.
# ============================================================================

resource "digitalocean_database_cluster" "cache" {
  # name: come appare nel pannello DO -> Databases
  name = "${var.name_prefix}-cache"

  # engine: "valkey" e' l'unico engine cache disponibile su DO managed.
  # Storicamente esisteva "redis", discontinuato il 30/06/2025.
  engine = "valkey"

  # version: ultima major stabile (8 al momento, controllare nel pannello DO)
  version = var.cache_engine_version

  # size: slug della taglia del cluster
  # db-s-1vcpu-1gb = ~$15/mese, basic tier (sufficiente per la lezione)
  size = var.cache_size

  # region: stessa dei nodi app per latenza minima
  region = var.region

  # node_count: 1 = nodo singolo (no HA, ma cheap)
  # Per produzione: 2+ per failover automatico
  node_count = var.cache_node_count

  # private_network_uuid: collega il cluster alla nostra VPC.
  # I nodi app lo raggiungono via hostname privato (.b.db.ondigitalocean.com)
  private_network_uuid = digitalocean_vpc.main.id

  # eviction_policy: cosa fare quando la cache e' piena
  # allkeys_lru = scarta le chiavi meno usate di recente (sensato per cache)
  eviction_policy = "allkeys_lru"

  tags = local.common_tags
}

# Firewall del cluster Valkey: solo le Droplet con tag "devops-course"
# possono connettersi. I nodi app hanno questo tag (vedi local.common_tags).
resource "digitalocean_database_firewall" "cache_fw" {
  cluster_id = digitalocean_database_cluster.cache.id

  rule {
    type  = "tag"
    value = "devops-course"
  }
}
