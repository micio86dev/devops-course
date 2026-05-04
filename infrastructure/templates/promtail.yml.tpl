server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://${monitoring_node_ip}:3100/loki/api/v1/push

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 15s
    relabel_configs:
      - source_labels: [__meta_docker_container_name]
        regex: '/?(.*)'
        target_label: container
      - source_labels: [__meta_docker_compose_service]
        target_label: service
      - target_label: node
        replacement: '${node_name}'
    pipeline_stages:
      - docker: {}

  - job_name: system
    static_configs:
      - targets: [localhost]
        labels:
          job: varlogs
          node: '${node_name}'
          __path__: /var/log/syslog
