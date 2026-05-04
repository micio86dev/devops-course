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

output "db_private_ip" {
  description = "IP privato (VPC) del nodo DB. Usato dagli app node per montare NFS."
  value       = digitalocean_droplet.db.ipv4_address_private
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

# ============================================================================
# Output del Managed MySQL
# Sei output coerenti con i secret richiesti da GitHub Actions:
# DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_SSL_CA.
# ============================================================================

output "mysql_private_host" {
  description = "Hostname privato del Managed MySQL (visibile solo dalla VPC)"
  value       = digitalocean_database_cluster.mysql.private_host
}

output "mysql_port" {
  description = "Porta del cluster MySQL (di default 25060 sui Managed DO)"
  value       = digitalocean_database_cluster.mysql.port
}

output "mysql_user" {
  description = "Username applicativo creato nel cluster"
  value       = digitalocean_database_user.app.name
}

output "mysql_password" {
  description = "Password generata per l'utente applicativo"
  value       = digitalocean_database_user.app.password
  # sensitive: la password e' segreta. Per leggerla esplicitamente:
  #   terraform output -raw mysql_password
  sensitive = true
}

output "mysql_database" {
  description = "Nome del database applicativo"
  value       = digitalocean_database_db.app.name
}

output "mysql_ca_certificate" {
  description = "Certificato CA del cluster in PEM. Da base64-encodare (terraform output -raw mysql_ca_certificate | base64) per il secret DB_SSL_CA."
  # Il CA cert vive su un data source dedicato (non sul cluster stesso).
  # L'attributo .certificate e' base64; lo decodifichiamo per esporre PEM.
  value = base64decode(data.digitalocean_database_ca.mysql.certificate)
  # sensitive: tecnicamente e' pubblico (e' un CA cert), ma marcandolo
  # sensitive evitiamo che finisca nei log di terraform plan/apply.
  sensitive = true
}

output "project_name" {
  description = "Conferma del Project DO dove sono andate le resource"
  value       = data.digitalocean_project.course.name
}
