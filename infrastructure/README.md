# Lezione: LB + 2 nodi app + Managed MySQL + Managed Valkey + Monitoring

> **Architettura managed:** tutto il database è su DigitalOcean Managed MySQL. La cache è su
> Managed Valkey. Un nodo monitoring dedicato ospita Prometheus, Grafana, Loki e Alertmanager.

---

## La struttura della cartella

```
infrastructure/
├── .gitignore
├── terraform.tfvars            ← VALORI segreti (gitignored!)
├── terraform-example.tfvars    ← template da copiare
│
├── provider.tf                 ← Terraform + provider DigitalOcean + null
├── variables.tf                ← dichiarazione delle variabili
├── locals.tf                   ← tag comuni
├── outputs.tf                  ← cosa stampare a fine apply
│
├── project.tf                  ← Project DO + assegnazione resource
├── ssh.tf                      ← chiave SSH
├── network.tf                  ← VPC privata
│
├── droplet-app.tf              ← nodi applicativi (×2)
├── droplet-monitoring.tf       ← nodo monitoring (Prometheus + Grafana + Loki)
├── load-balancer.tf            ← Load Balancer pubblico
│
├── database-valkey.tf          ← cluster Managed Valkey
├── database-mysql.tf           ← cluster Managed MySQL
│
├── firewall-app.tf             ← regole firewall nodi app
├── firewall-monitoring.tf      ← regole firewall nodo monitoring
│
├── null-resource-node-agents.tf ← installa node_exporter + cAdvisor + Promtail sui nodi app
│
└── cloud-init/
│   ├── app.yaml                ← bootstrap nodi app (Docker + env files MySQL/Valkey)
│   └── monitoring.yaml         ← bootstrap nodo monitoring (tutti i servizi via Docker Compose)
│
└── templates/
    ├── promtail.yml.tpl        ← config Promtail per-nodo (vars: monitoring_node_ip, node_name)
    └── agents-compose.yml      ← Docker Compose per agenti sui nodi app
```

---

## Schema dell'infrastruttura

```
                          🌐 Internet
                              │
                              ▼  HTTP :80
                     ┌────────────────┐
                     │ Load Balancer  │  ← unico IP pubblico per il traffico app
                     └────┬───────┬───┘
                          │       │  least-connections verso :5001
       ╔══════════════════│═══════│═════════════════════════════════╗
       ║   VPC privata    ▼       ▼   10.10.10.0/24                ║
       ║   ┌──────────────┐    ┌──────────────┐                    ║
       ║   │ App Node 1   │    │ App Node 2   │                    ║
       ║   │ Docker:5001  │    │ Docker:5001  │                    ║
       ║   │ node_exporter│    │ node_exporter│                    ║
       ║   │ cAdvisor     │    │ cAdvisor     │                    ║
       ║   │ Promtail     │    │ Promtail     │                    ║
       ║   └──┬───┬───┬───┘    └──┬───┬───┬───┘                    ║
       ║      │   │   │           │   │   │                        ║
       ║  MySQL│  Valkey Loki  MySQL  Valkey Loki                  ║
       ║  :25060 :25061 :3100 :25060 :25061 :3100                  ║
       ║      │   │   │           │   │   │                        ║
       ║   ┌──▼───▼───▼───────────▼───▼───▼──┐  ┌──────────────┐  ║
       ║   │  Managed MySQL   Managed Valkey  │  │  Monitoring  │  ║
       ║   │  (DigitalOcean)  (DigitalOcean)  │  │  Prometheus  │  ║
       ║   │  port 25060      port 25061      │  │  Grafana :80 │  ║
       ║   └─────────────────────────────────┘  │  Loki :3100  │  ║
       ║                                         │  Alertmanager│  ║
       ║                                         └──────────────┘  ║
       ╚═════════════════════════════════════════════════════════════╝
```

---

## Scelte architetturali

| Componente         | Strategia    | Motivo                                                                         |
| ------------------ | ------------ | ------------------------------------------------------------------------------ |
| **DB (MySQL)**     | Managed      | Alta disponibilità, backup automatici, no patching manuale                     |
| **Cache (Valkey)** | Managed      | Unica opzione cache managed su DO dal 30/06/2025; backup e password automatici |
| **Monitoring**     | Self-managed | Prometheus/Grafana/Loki non esistono come managed su DO; didatticamente forte  |

---

## Nota didattica: Redis → Valkey

Su DigitalOcean dal 30 giugno 2025 **non esiste più Managed Redis**. È stato sostituito da
Managed Valkey (fork open-source di Redis 7.2.4 sotto BSD pulita, supportato da Linux Foundation).

Per la nostra app Python:

- Il client `redis-py` parla con Valkey **senza modifiche al codice**.
- L'unica differenza pratica: Valkey su DO **richiede TLS e password** (`rediss://` con doppia "s").
- Tutta questa complessità è incapsulata in `REDIS_URL`.

---

## Step 0 — Setup sicuro

**0.1** Pannello DO → **Manage → Projects → New Project** → nome: `devops-course`

**0.2** **API → Generate New Token** con custom scopes:

- `droplet`, `ssh_key`, `firewall`, `vpc`, `load_balancer`, `project`, `tag`
- `database` — necessario per i cluster MySQL e Valkey

Scadenza 30 giorni.

**0.3** Sei già nella cartella `infrastructure/`.

---

## Pre-flight checklist

| #   | Check                          | Come verificare                      |
| --- | ------------------------------ | ------------------------------------ |
| 1   | Token con scope `database`     | Pannello DO → API                    |
| 2   | Project `devops-course` esiste | Pannello → Manage → Projects         |
| 3   | `terraform.tfvars` compilato   | `cat terraform.tfvars` (mai su git!) |
| 4   | Tutti i file `.tf` ci sono     | `ls -la *.tf cloud-init/ templates/` |
| 5   | File ASCII puro                | `file *.tf cloud-init/*.yaml`        |

---

## Comandi Terraform

```bash
terraform init
terraform fmt
terraform validate
terraform plan -out=tfplan
terraform apply tfplan
```

---

## Verifica del funzionamento

```bash
LB_IP=$(terraform output -raw load_balancer_ip)
curl -i http://$LB_IP/healthz
# Risposta attesa: HTTP/1.1 200 OK

# Grafana
open http://$(terraform output -raw monitoring_node_public_ip)
# Login: admin / <grafana_password da tfvars>
```

---

## GitHub Secrets da settare dopo `terraform apply`

Dalla cartella `infrastructure/`:

```bash
# Secret di deploy (stessi per staging e production)
gh secret set DEPLOY_HOSTS   -e staging --body "$(terraform output -json app_node_ips | jq -r 'join(",")')"
gh secret set DEPLOY_USER    -e staging --body "root"
gh secret set DEPLOY_SSH_KEY -e staging --body "$(cat ~/.ssh/id_ed25519)"

# Secret MySQL (per rotazione credenziali senza re-apply Terraform)
gh secret set DB_HOST     -e staging --body "$(terraform output -raw mysql_private_host)"
gh secret set DB_PORT     -e staging --body "$(terraform output -raw mysql_port)"
gh secret set DB_NAME     -e staging --body "$(terraform output -raw mysql_database)"
gh secret set DB_USER     -e staging --body "$(terraform output -raw mysql_user)"
gh secret set DB_PASSWORD -e staging --body "$(terraform output -raw mysql_password)"
gh secret set DB_SSL_CA   -e staging --body "$(terraform output -raw mysql_ca_certificate | base64)"
```

---

## Costi (fra1, maggio 2026)

| Componente                           | Costo/mese |
| ------------------------------------ | ---------- |
| 2 × Droplet app (s-1vcpu-1gb)        | ~$12       |
| 1 × Droplet monitoring (s-1vcpu-2gb) | ~$12       |
| Load Balancer                        | ~$12       |
| Managed Valkey (db-s-1vcpu-1gb)      | ~$15       |
| Managed MySQL (db-s-1vcpu-1gb)       | ~$15       |
| **Totale**                           | **~$66**   |

---

## A fine lezione

```bash
terraform destroy
```

⚠️ I cluster managed ci mettono **2-3 minuti in più** delle Droplet a essere distrutti.
Aspetta che `destroy` finisca completamente prima di chiudere il terminale.

---

## Compiti per casa

1. 🥉 **Aggiungi un terzo nodo app** (`count = 3` in `droplet-app.tf`)
2. 🥈 **Aggiungi un read replica** al cluster Valkey con `node_count = 2`
3. 🥇 **HTTPS sul LB** con certificato Let's Encrypt
4. 🏆 **Alert Slack**: configura `alertmanager_slack_url` in `terraform.tfvars`
5. 🏆🏆 **Grafana dashboard custom**: aggiungi un pannello con le query sull'app Flask
