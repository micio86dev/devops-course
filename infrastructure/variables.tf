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

variable "container_port" {
  description = "Porta INTERNA al container (quella in EXPOSE del Dockerfile)"
  type        = number
  # 5000 perché il Dockerfile della todo-app fa EXPOSE 5000
  default = 5000
}

variable "host_port" {
  description = "Porta esterna sulla Droplet (mappata al container)"
  type        = number
  # 5001 per coerenza con il setup di sviluppo locale
  default = 5001
}

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