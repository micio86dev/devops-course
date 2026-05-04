# Monitoring Stack

Prometheus · Grafana · Loki · Alertmanager

---

## Architecture

```
Internet
    │
    ▼
DO Load Balancer (port 80)
    │
    ├──► app-1 (devops-course-app-1)
    │       node_exporter :9100  ◄── Prometheus scrapes (VPC only)
    │       cAdvisor      :8080  ◄── Prometheus scrapes (VPC only)
    │       Promtail      :9080  ──► Loki push :3100
    │
    └──► app-2 (devops-course-app-2)
            node_exporter :9100  ◄── Prometheus scrapes (VPC only)
            cAdvisor      :8080  ◄── Prometheus scrapes (VPC only)
            Promtail      :9080  ──► Loki push :3100

devops-course-monitoring (public IP)
    nginx :80  ──► Grafana :3000 (127.0.0.1 only)
    Prometheus   :9090 (internal Docker network)
    Loki         :3100 (VPC + Docker network)
    Alertmanager :9093 (internal Docker network)
    mysqld_exporter ──► MySQL managed :25060 (VPC)
    redis_exporter  ──► Valkey managed :25061 (VPC)
    blackbox        ──► LB public IP (HTTP probe)
```

---

## Local quickstart

```bash
# Avvia stack app + monitoring (tutto in locale, no VPC)
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Grafana: http://localhost:3000  (admin / admin)
# Prometheus: http://localhost:9090
# Loki: http://localhost:3100
```

I config locali sono in `monitoring/dev/` — nessuna credenziale di produzione richiesta.

---

## Production deployment

```bash
cd infrastructure

# 1. Aggiungi a terraform.tfvars le nuove variabili (vedi terraform-example.tfvars)
#    ssh_private_key, grafana_password, mysql_exporter_dsn, valkey_exporter_uri

# 2. Verifica il piano
terraform plan

# 3. Applica — crea il nodo monitoring + aggiorna i firewall + installa gli agent
terraform apply

# 4. Leggi l'URL Grafana
terraform output grafana_url
```

Al termine, cloud-init sul nodo monitoring installa Docker, scrive tutti i config,
avvia docker compose, e scarica i dashboard community da grafana.com.
Tempo stimato dal boot al ready: ~5 minuti.

---

## Accesso a Grafana

| Ambiente   | URL                              | Credenziali                |
| ---------- | -------------------------------- | -------------------------- |
| Produzione | `http://<monitoring-public-ip>/` | admin / `grafana_password` |
| Locale     | `http://localhost:3000`          | admin / admin              |

**Ruotare la password admin in produzione:**

```bash
# Via SSH sul nodo monitoring
docker exec -it monitoring-grafana-1 grafana-cli admin reset-admin-password NUOVA_PASS
```

---

## Aggiungere un nuovo scrape target

1. Apri `/opt/monitoring/prometheus/prometheus.yml` sul nodo monitoring
2. Aggiungi il job nella sezione `scrape_configs`
3. Ricarica Prometheus senza restart:
   ```bash
   curl -X POST http://localhost:9090/-/reload
   ```
4. Se il target è su un nodo app, aggiungi la regola firewall in `infrastructure/firewall-app.tf`
5. Ricordati di aggiornare anche il compose locale in `docker-compose.monitoring.yml`

---

## Aggiungere una nuova alert rule

1. Apri `/opt/monitoring/prometheus/rules/infrastructure.yml` (o crea un nuovo `.yml`)
2. Aggiungi la rule seguendo il formato esistente
3. Valida la sintassi:
   ```bash
   docker exec monitoring-prometheus-1 promtool check rules /etc/prometheus/rules/infrastructure.yml
   ```
4. Ricarica:
   ```bash
   curl -X POST http://localhost:9090/-/reload
   ```

Per modificare le rule in modo permanente, modifica il file template in
`infrastructure/cloud-init/monitoring.yaml` e ri-applica Terraform.

---

## Variabili d'ambiente richieste

| Variabile                    | Dove va          | Descrizione                                     |
| ---------------------------- | ---------------- | ----------------------------------------------- |
| `ssh_private_key`            | terraform.tfvars | Chiave SSH privata per remote-exec sui nodi app |
| `grafana_password`           | terraform.tfvars | Password admin Grafana                          |
| `mysql_exporter_dsn`         | terraform.tfvars | `user:pass@tcp(host:25060)/`                    |
| `valkey_exporter_uri`        | terraform.tfvars | `rediss://default:pass@host:25061`              |
| `alertmanager_slack_url`     | terraform.tfvars | Webhook Slack (opzionale, default vuoto)        |
| `alertmanager_slack_channel` | terraform.tfvars | Canale Slack (default `#alerts`)                |

Valori MySQL: `terraform output -raw mysql_password` e `terraform output -raw mysql_private_host`
Valori Valkey: `terraform output cache_uri`

---

## Hot-reload Prometheus

```bash
# SSH sul nodo monitoring, poi:
curl -X POST http://localhost:9090/-/reload
```

---

## Troubleshooting

**Prometheus target DOWN**

```bash
# SSH sul nodo monitoring
# Verifica connettività al nodo app sulla porta giusta
curl http://<app-node-private-ip>:9100/metrics | head
# Verifica regole firewall su DO → network → firewalls
```

**Loki non riceve log**

```bash
# Sui nodi app: verifica che Promtail sia running
docker ps | grep promtail
docker logs $(docker ps -q -f name=promtail)
# Verifica che la porta 3100 sia raggiungibile dal nodo app
curl http://<monitoring-private-ip>:3100/ready
```

**mysqld_exporter non si connette**

```bash
# Sul nodo monitoring
docker logs monitoring-mysqld_exporter-1
# Verifica il DSN in /opt/monitoring/.env
# Assicurati che il firewall MySQL permetta il tag "devops-course"
```

**Dashboard Grafana vuoti**

```bash
# Verifica che i JSON dei dashboard siano stati scaricati
ls /opt/monitoring/grafana/provisioning/dashboards/*.json
# Se mancano, ri-scaricali manualmente:
curl -sL "https://grafana.com/api/dashboards/1860/revisions/latest/download" \
  -o /opt/monitoring/grafana/provisioning/dashboards/node-exporter-full.json
```
