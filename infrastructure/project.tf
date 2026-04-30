# ============================================================================
# project.tf
# 1. Legge il Project esistente (creato a mano nel pannello DO).
# 2. Assegna le resource Terraform a quel Project.
# Senza il punto 2, le resource finiscono nel "default project"!
# ============================================================================

# data: legge informazioni su una resource ESISTENTE su DO.
# NON crea nulla, solo legge.
data "digitalocean_project" "course" {
  # name: deve combaciare ESATTAMENTE con quello nel pannello DO
  # (case-sensitive, spazi inclusi)
  name = var.project_name
}

# Assegna le resource al Project.
# Riferimento incrociato: legge resource definite in altri file .tf.
resource "digitalocean_project_resources" "course" {
  # project: ID del progetto (preso dal data source sopra)
  project = data.digitalocean_project.course.id

  # resources: lista di URN (Uniform Resource Name) da assegnare.
  # URN formato: do:droplet:12345, do:dbaas:abc-def, ...
  # concat(): unisce piu' liste in una sola
  resources = concat(
    # [*].urn = lista degli URN di tutti gli app nodes
    digitalocean_droplet.app[*].urn,
    [
      # Droplet DB self-managed (con SQLite + NFS)
      digitalocean_droplet.db.urn,

      # CAMBIO RISPETTO ALLA VERSIONE PRECEDENTE:
      # niente piu' digitalocean_droplet.cache.urn (la Droplet non esiste piu')
      # al suo posto: l'URN del cluster Valkey managed
      digitalocean_database_cluster.cache.urn,

      digitalocean_loadbalancer.public.urn,
    ]
  )
  # Nota: VPC, SSH key e Firewall NON vanno qui
  # (limitazione dell'API DigitalOcean - accetta solo certi tipi)
}
