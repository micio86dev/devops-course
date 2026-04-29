# ============================================================================
# outputs.tf
# Valori stampati al termine di `terraform apply`.
# Recuperabili in qualsiasi momento con `terraform output [nome]`.
# ============================================================================

output "load_balancer_ip" {
  description = "IP pubblico del Load Balancer (l'unico esposto agli utenti)"
  # .ip e' l'attributo del LB. Disponibile solo dopo creazione.
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
  description = "IP pubblico del nodo DB self-managed (per SSH di debug)"
  value       = digitalocean_droplet.db.ipv4_address
}

# CAMBIO RISPETTO ALLA VERSIONE PRECEDENTE:
# niente piu' cache_node_ip (la Droplet non esiste piu').
# Al suo posto: hostname privato del cluster Valkey + URI sensibile.

output "cache_host" {
  description = "Hostname privato del Managed Valkey (visibile solo dalla VPC)"
  value       = digitalocean_database_cluster.cache.private_host
}

output "cache_uri" {
  description = "Connection URI completa di Valkey (con password!)"
  value       = digitalocean_database_cluster.cache.private_uri
  # sensitive = true: nasconde il valore nei log
  # Per vederla: `terraform output cache_uri` (la stampa esplicitamente)
  sensitive = true
}

output "project_name" {
  description = "Conferma del Project DO dove sono andate le resource"
  value       = data.digitalocean_project.course.name
}
