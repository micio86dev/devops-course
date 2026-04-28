variable "do_token" {
  description = "Token API di DigitalOcean"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "Contenuto della tua chiave SSH pubblica"
  type        = string
}

variable "region" {
  description = "Regione DigitalOcean dove creare il server"
  type        = string
  default     = "fra1" # Francoforte — vicina all'Italia
}

variable "droplet_size" {
  description = "Taglia del server"
  type        = string
  default     = "s-1vcpu-1gb" # ~$6 al mese, basta per la demo
}

variable "docker_image" {
  description = "Nome completo dell'immagine Docker dell'app"
  type        = string
  # Esempio: "miciodev/todo-app:latest"
}