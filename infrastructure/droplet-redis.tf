# ============================================================================
# droplet-redis.tf
# Droplet del nodo Redis: cache in-memory accessibile dai nodi app.
# ============================================================================

resource "digitalocean_droplet" "redis" {
  name      = "${var.name_prefix}-redis"
  image     = "ubuntu-24-04-x64"
  region    = var.region
  size      = var.droplet_size
  vpc_uuid  = digitalocean_vpc.main.id
  ssh_keys  = [digitalocean_ssh_key.default.id]
  user_data = file("${path.module}/cloud-init/redis.yaml")
  tags      = local.common_tags
}