# ============================================================================
# project.tf
# 1. Legge il Project esistente (creato a mano allo Step 0.1).
# 2. Assegna le resource Terraform a quel Project.
# Senza il punto 2, le resource finiscono nel "default project"!
# ============================================================================

# data: legge informazioni su una resource ESISTENTE su DO.
# NON crea nulla, solo legge.
data "digitalocean_project" "course" {
  # name: deve combaciare ESATTAMENTE con quello nel pannello
  # (case-sensitive, spazi inclusi)
  name = var.project_name
}

# Assegna le resource al Project.
# Riferimento incrociato: legge resource definite in altri file .tf.
resource "digitalocean_project_resources" "course" {
  # project: ID del progetto (preso dal data source sopra)
  project = data.digitalocean_project.course.id

  # resources: lista di URN (Uniform Resource Name) da assegnare.
  # URN formato: do:droplet:12345, do:loadbalancer:abc-def, ...
  # concat(): unisce più liste in una sola
  resources = concat(
    # [*].urn = lista degli URN di tutti gli app nodes
    digitalocean_droplet.app[*].urn,
    [
      # Singoli URN: dentro [...] perché concat() vuole liste
      digitalocean_droplet.db.urn,
      digitalocean_droplet.redis.urn,
      digitalocean_loadbalancer.public.urn,
    ]
  )
  # Nota: VPC, SSH key e Firewall NON vanno qui
  # (limitazione dell'API DigitalOcean — accetta solo certi tipi)
}