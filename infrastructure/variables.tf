# ============================================================================
# variables.tf
# Dichiara TUTTE le variabili usate dagli altri file .tf.
# I valori reali vanno in terraform.tfvars (gitignored).
# ============================================================================

variable "do_token" {
  # description: documentazione, appare in `terraform plan` e nei tool IDE
  description = "Token API DigitalOcean con custom scopes"
  # type: forza Terraform a validare il tipo di valore passato
  type = string
  # sensitive = true: nasconde il valore nei log e nell'output di `plan`
  # IMPORTANTISSIMO per token, password, chiavi private
  sensitive = true
}

variable "ssh_public_key" {
  description = "Contenuto della chiave SSH pubblica (es. ~/.ssh/id_ed25519.pub)"
  type        = string
  # nessun default: l'utente DEVE fornirla in terraform.tfvars
}

variable "region" {
  description = "Regione DigitalOcean (es. fra1, ams3, nyc1)"
  type        = string
  # default: se l'utente non specifica nulla, usa fra1 (Francoforte)
  default = "fra1"
}

variable "droplet_size" {
  description = "Taglia delle Droplet (slug DigitalOcean)"
  type        = string
  # s-1vcpu-1gb = ~$6/mese, sufficiente per la lezione
  default = "s-1vcpu-1gb"
}

variable "docker_image" {
  description = "Immagine Docker dell'app (es. miciodev/todo-app:latest)"
  type        = string
  # nessun default: dipende dal progetto specifico
}

variable "container_name" {
  description = "Nome del container Docker che gira sui nodi app"
  type        = string
  # docker-todo-prod = nome usato anche nel docker-compose.prod.yml
  default = "docker-todo-prod"
}

variable "container_port" {
  description = "Porta INTERNA al container (quella in EXPOSE del Dockerfile)"
  type        = number
  # 5000 perche' il Dockerfile della todo-app fa EXPOSE 5000
  default = 5000
}

variable "host_port" {
  description = "Porta esterna sulla Droplet (mappata al container)"
  type        = number
  # 5001 per coerenza con il setup di sviluppo locale
  default = 5001
}

# ============================================================================
# Variabili NUOVE per il Managed Valkey
# ============================================================================

variable "cache_engine_version" {
  description = "Versione Valkey del Managed Caching"
  type        = string
  # 8 = ultima major stabile (aprile 2026)
  default = "8"
}

variable "cache_size" {
  description = "Slug della size del cluster Valkey"
  type        = string
  # db-s-1vcpu-1gb = ~$15/mese, basic tier
  default = "db-s-1vcpu-1gb"
}

variable "cache_node_count" {
  description = "Numero di nodi del cluster Valkey (1 = no HA)"
  type        = number
  # 1 = nodo singolo. Produzione: 2+ per failover automatico.
  default = 1
}

# ============================================================================
# Variabili NUOVE per il Managed MySQL
# ============================================================================

variable "mysql_engine_version" {
  description = "Versione major di MySQL (managed)"
  type        = string
  # 8 e' l'unica versione managed disponibile su DO oggi
  default = "8"
}

variable "mysql_size" {
  description = "Slug della size del cluster MySQL"
  type        = string
  # db-s-1vcpu-1gb = ~$15/mese, basic tier (sufficiente per la lezione)
  default = "db-s-1vcpu-1gb"
}

variable "mysql_node_count" {
  description = "Numero di nodi del cluster MySQL (1 = no HA)"
  type        = number
  # 1 = nodo singolo. Produzione: 2+ per failover automatico.
  default = 1
}

variable "mysql_database_name" {
  description = "Nome del database applicativo dentro al cluster"
  type        = string
  default     = "todos"
}

variable "mysql_user_name" {
  description = "Nome dell'utente applicativo creato nel cluster"
  type        = string
  default     = "todoapp"
}

# ============================================================================

variable "project_name" {
  description = "Nome del Project DigitalOcean (case-sensitive!)"
  type        = string
  # Deve combaciare ESATTAMENTE col nome nel pannello DO
  default = "devops-course"
}

variable "name_prefix" {
  description = "Prefisso per i nomi delle resource"
  type        = string
  default     = "devops-course"
}

# ============================================================================
# Variabili per il nodo monitoring
# ============================================================================

variable "ssh_private_key_path" {
  description = "Path alla chiave SSH privata (per remote-exec provisioner sui nodi app)"
  type        = string
  default     = "~/.ssh/id_ed25519"
}

variable "monitoring_droplet_size" {
  description = "Taglia della Droplet di monitoring"
  type        = string
  default     = "s-1vcpu-2gb"
}

variable "grafana_password" {
  description = "Password admin di Grafana"
  type        = string
  sensitive   = true
}

variable "valkey_exporter_uri" {
  description = "URI Valkey per redis_exporter: rediss://default:pass@host:25061"
  type        = string
  sensitive   = true
}

variable "alertmanager_slack_url" {
  description = "Webhook Slack per Alertmanager (lascia vuoto per disabilitare)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "alertmanager_slack_channel" {
  description = "Canale Slack per gli alert"
  type        = string
  default     = "#alerts"
}
