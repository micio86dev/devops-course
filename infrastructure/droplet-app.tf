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

    # CAMBIO RISPETTO ALLA VERSIONE PRECEDENTE:
    # niente piu' cache_private_ip (la Droplet non esiste piu').
    # Al suo posto: la connection URI privata del cluster Valkey managed.
    # Formato: rediss://default:PASSWORD@host:25061
    # La doppia "s" indica TLS (obbligatorio sui managed DO).
    cache_uri = digitalocean_database_cluster.cache.private_uri

    # Connection details del Managed MySQL: cloud-init li scrive in
    # /root/docker-todo/.env.mysql (mode 600). Sei valori (host/port/db/user/
    # password/ca_certificate) coerenti con i secret GitHub DB_*.
    mysql_private_host   = digitalocean_database_cluster.mysql.private_host
    mysql_port           = digitalocean_database_cluster.mysql.port
    mysql_database       = digitalocean_database_db.app.name
    mysql_user           = digitalocean_database_user.app.name
    mysql_password       = digitalocean_database_user.app.password
    mysql_ca_certificate = data.digitalocean_database_ca.mysql.certificate

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
    digitalocean_database_cluster.cache,
    digitalocean_database_cluster.mysql,
    digitalocean_database_db.app,
    digitalocean_database_user.app,
  ]
}
