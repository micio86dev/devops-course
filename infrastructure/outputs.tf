# ============================================================================
# outputs.tf
# Valori stampati al termine di `terraform apply`.
# Recuperabili in qualsiasi momento con `terraform output [nome]`.
# ============================================================================

output "load_balancer_ip" {
  description = "IP pubblico del Load Balancer (l'unico esposto agli utenti)"
  # .ip è l'attributo del LB. Disponibile solo dopo creazione.
  value = digitalocean_loadbalancer.public.ip
}

output "app_url" {
  description = "URL pronta da incollare nel browser"
  # Interpolazione: stringa con valori dinamici dentro
  value = "http://${digitalocean_loadbalancer.public.ip}"
}

output "app_node_ips" {
  description = "IP pubblici dei nodi app (per SSH di debug)"
  # [*].ipv4_address: lista degli IP pubblici di tutti gli app node
  value = digitalocean_droplet.app[*].ipv4_address
}

output "db_node_ip" {
  description = "IP pubblico del nodo DB"
  value       = digitalocean_droplet.db.ipv4_address
}

output "redis_node_ip" {
  description = "IP pubblico del nodo Redis"
  value       = digitalocean_droplet.redis.ipv4_address
}

output "project_name" {
  description = "Conferma del Project DO dove sono andate le resource"
  value       = data.digitalocean_project.course.name
}