output "droplet_ip" {
  description = "Indirizzo IP pubblico del server"
  value       = digitalocean_droplet.todo.ipv4_address
}

output "app_url" {
  description = "Link dove l'app è raggiungibile"
  value       = "http://${digitalocean_droplet.todo.ipv4_address}"
}

output "ssh_command" {
  description = "Comando SSH già pronto da copiare"
  value       = "ssh root@${digitalocean_droplet.todo.ipv4_address}"
}