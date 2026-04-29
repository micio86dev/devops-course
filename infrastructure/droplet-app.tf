# ============================================================================
# droplet-app.tf
# Nodi applicativi: count = 2 -> due Droplet identiche dietro al LB.
# ============================================================================

resource "digitalocean_droplet" "app" {
  # count: meta-argomento. Crea N copie identiche.
  # Le riferisci come: digitalocean_droplet.app[0], app[1]...
  count = 2

  # count.index: 0, 1, 2... per ogni iterazione.
  # +1 per nominarle "app-1" e "app-2" (piu' leggibile di app-0)
  name = "${var.name_prefix}-app-${count.index + 1}"

  image    = "ubuntu-24-04-x64"
  region   = var.region
  size     = var.droplet_size
  vpc_uuid = digitalocean_vpc.main.id
  ssh_keys = [digitalocean_ssh_key.default.id]

  # templatefile(): come file(), ma con sostituzione di variabili.
  # Le ${...} dentro al file YAML vengono rimpiazzate con i valori passati.
  user_data = templatefile("${path.module}/cloud-init/app.yaml", {
    docker_image   = var.docker_image
    container_name = var.container_name

    # ipv4_address_private: IP della Droplet sulla VPC (NON quello pubblico!)
    db_private_ip = digitalocean_droplet.db.ipv4_address_private

    # CAMBIO RISPETTO ALLA VERSIONE PRECEDENTE:
    # niente piu' cache_private_ip (la Droplet non esiste piu').
    # Al suo posto: la connection URI privata del cluster Valkey managed.
    # Formato: rediss://default:PASSWORD@host:25061
    # La doppia "s" indica TLS (obbligatorio sui managed DO).
    cache_uri = digitalocean_database_cluster.cache.private_uri

    # Passa anche le porte al template (per docker run -p)
    host_port      = var.host_port
    container_port = var.container_port
  })

  # Tag include "devops-course": OBBLIGATORIO per il firewall del cluster
  # Valkey managed (vedi database-valkey.tf, regola tag-based).
  tags = local.common_tags

  # depends_on: forza ordine di creazione esplicito.
  # Terraform di solito lo deduce dai riferimenti, qui lo rendiamo esplicito.
  depends_on = [
    digitalocean_droplet.db,
    digitalocean_database_cluster.cache,
  ]
}
