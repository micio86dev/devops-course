# ============================================================================
# droplet-monitoring.tf
# Droplet dedicata allo stack di monitoring:
# Prometheus · Grafana · Loki · Alertmanager · mysqld_exporter · redis_exporter
# Provisioning via cloud-init; tutti i config file vengono scritti al boot.
# ============================================================================

resource "digitalocean_droplet" "monitoring" {
  name     = "${var.name_prefix}-monitoring"
  image    = "ubuntu-24-04-x64"
  region   = var.region
  size     = var.monitoring_droplet_size
  vpc_uuid = digitalocean_vpc.main.id
  ssh_keys = [digitalocean_ssh_key.default.id]
  tags     = concat(local.common_tags, ["monitoring"])

  user_data = templatefile("${path.module}/cloud-init/monitoring.yaml", {
    app_node_1_ip              = digitalocean_droplet.app[0].ipv4_address_private
    app_node_2_ip              = digitalocean_droplet.app[1].ipv4_address_private
    lb_ip                      = digitalocean_loadbalancer.public.ip
    grafana_password           = var.grafana_password
    mysql_exporter_dsn         = var.mysql_exporter_dsn
    valkey_exporter_uri        = var.valkey_exporter_uri
    alertmanager_slack_url     = var.alertmanager_slack_url
    alertmanager_slack_channel = var.alertmanager_slack_channel
  })

  depends_on = [
    digitalocean_droplet.app,
    digitalocean_database_cluster.mysql,
    digitalocean_database_cluster.cache,
    digitalocean_loadbalancer.public,
  ]
}
