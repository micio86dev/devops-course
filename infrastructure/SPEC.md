# Infrastructure Specification — docker-todo on DigitalOcean

> **Spec-Driven Development (SDD)**: each assertion below defines the _expected_ state of the
> infrastructure after `terraform apply`. If an assertion fails, the Terraform code or cloud-init
> must be corrected — never the spec.

---

## 1. Provider & State

| Spec ID | Assertion                                                        |
| ------- | ---------------------------------------------------------------- |
| TF-01   | Provider: `digitalocean` ≥ 2.40, locked in `.terraform.lock.hcl` |
| TF-02   | Terraform version constraint: `>= 1.6.0`                         |
| TF-03   | `terraform.tfvars` is **gitignored** and never committed         |
| TF-04   | `terraform.tfstate` is **gitignored** and never committed        |
| TF-05   | `terraform validate` exits 0 with no errors                      |

---

## 2. Network

| Spec ID | Assertion                                                                 |
| ------- | ------------------------------------------------------------------------- |
| NET-01  | VPC CIDR `10.10.10.0/24` in region `fra1` (configurable via `var.region`) |
| NET-02  | All compute resources (Droplets, LB, Valkey) are attached to this VPC     |
| NET-03  | Only the Load Balancer has a public IP exposed to the internet (HTTP)     |
| NET-04  | App Droplets have public IPs for SSH access only                          |
| NET-05  | Monitoring Droplet has a public IP for SSH and Grafana (HTTP :80)         |

---

## 3. Load Balancer

| Spec ID | Assertion                                                                   |
| ------- | --------------------------------------------------------------------------- |
| LB-01   | Accepts traffic on port **80** (HTTP) from 0.0.0.0/0                        |
| LB-02   | Forwards to app nodes on port **5001** (host-mapped Docker port)            |
| LB-03   | Algorithm: least-connections                                                |
| LB-04   | Health check: `GET /healthz` on port 5001, interval 10 s, timeout 5 s       |
| LB-05   | Unhealthy threshold: 3 consecutive failures; healthy threshold: 2 successes |
| LB-06   | Only healthy app nodes receive traffic                                      |

---

## 4. App Nodes (×2)

| Spec ID | Assertion                                                                  |
| ------- | -------------------------------------------------------------------------- |
| APP-01  | 2 Droplets: `devops-course-app-1`, `devops-course-app-2`                   |
| APP-02  | Image: `ubuntu-24-04-x64`; size: `s-1vcpu-1gb`; region: same as VPC        |
| APP-03  | Tags include `devops-course` (required for Valkey firewall rule)           |
| APP-04  | Docker and Docker Compose plugin installed via `apt` (docker.io)           |
| APP-05  | Directory `/root/docker-todo/` exists after provisioning                   |
| APP-06  | `/root/docker-todo/.env.valkey` contains `REDIS_URL=rediss://…` (mode 600) |
| APP-07  | `/root/docker-todo/.env.mysql` contains `DB_*` connection vars (mode 600)  |
| APP-08  | `/root/docker-todo/mysql-ca.pem` contains MySQL CA certificate (mode 644)  |
| APP-09  | No application container running at provision time — CI/CD deploys the app |

### App node firewall

| Spec ID   | Assertion                                                                         |
| --------- | --------------------------------------------------------------------------------- |
| FW-APP-01 | Inbound SSH (port 22) allowed from 0.0.0.0/0 (needed for CI/CD deploy)            |
| FW-APP-02 | Inbound HTTP (port 5001) allowed **only** from the Load Balancer (tag-based rule) |
| FW-APP-03 | All outbound TCP/UDP allowed (Docker image pulls, MySQL, Valkey)                  |
| FW-APP-04 | No other inbound ports open                                                       |

---

## 5. Managed Valkey Cluster

| Spec ID | Assertion                                                                                |
| ------- | ---------------------------------------------------------------------------------------- |
| VAL-01  | Engine: `valkey` version 8 (DigitalOcean managed; Redis 7.2.4-compatible)                |
| VAL-02  | Cluster name: `devops-course-cache`                                                      |
| VAL-03  | Size: `db-s-1vcpu-1gb`; `node_count = 1` (no HA — course demo)                           |
| VAL-04  | Attached to the VPC via `private_network_uuid`                                           |
| VAL-05  | Eviction policy: `allkeys_lru`                                                           |
| VAL-06  | Connection: `rediss://default:<password>@<private-host>:25061` (TLS mandatory, double-s) |
| VAL-07  | Firewall rule: only Droplets tagged `devops-course` can connect (port 25061)             |
| VAL-08  | `terraform output cache_uri` reveals the full URI (sensitive, not shown in plan)         |
| VAL-09  | App nodes can reach the cluster; app does **not** use it (infrastructure demo only)      |

---

## 6. Outputs (post `terraform apply`)

| Output                      | Description                                                                     |
| --------------------------- | ------------------------------------------------------------------------------- |
| `load_balancer_ip`          | Public IP of the LB — set as `DEPLOY_HOSTS` after removing the LB from the list |
| `app_url`                   | `http://<lb-ip>` — public URL of the application                                |
| `app_node_ips`              | List of public IPs of app nodes → use as `DEPLOY_HOSTS` in GitHub Secrets       |
| `cache_host`                | Private hostname of Valkey (VPC-only)                                           |
| `cache_uri`                 | Full Valkey connection URI (sensitive)                                          |
| `mysql_private_host`        | Private hostname of Managed MySQL (VPC-only)                                    |
| `mysql_port`                | MySQL port (25060)                                                              |
| `mysql_user`                | Application user name                                                           |
| `mysql_password`            | Application user password (sensitive)                                           |
| `mysql_database`            | Application database name                                                       |
| `mysql_ca_certificate`      | MySQL CA certificate PEM (sensitive; base64-encode for DB_SSL_CA secret)        |
| `monitoring_node_public_ip` | Public IP of monitoring node (Grafana, SSH)                                     |
| `grafana_url`               | `http://<monitoring-ip>` — Grafana UI                                           |
| `project_name`              | DigitalOcean project the resources belong to                                    |

---

## 7. Bootstrap Flow (cloud-init sequence on app nodes)

```
1. apt update + upgrade
2. Install: ca-certificates, curl, gnupg
3. Write /root/docker-todo/mysql-ca.pem (MySQL CA cert, mode 644)
4. Install Docker via apt (docker.io + docker-compose-v2)
5. Enable and start Docker daemon
6. mkdir -p /root/docker-todo
7. Write REDIS_URL=<cache_uri> to /root/docker-todo/.env.valkey (mode 600)
8. Write DB_* vars to /root/docker-todo/.env.mysql (mode 600)
```

At this point the node is **ready to receive a CI/CD deploy**. No app container runs yet.

---

## 8. First Deploy Prerequisites

After `terraform apply` succeeds, before the first CD run:

1. Add GitHub Secrets (environment `staging` / `production`):
   - `DEPLOY_HOSTS` ← `terraform output -json app_node_ips | jq -r 'join(",")'`
   - `DEPLOY_USER` ← `root`
   - `DEPLOY_SSH_KEY` ← contents of your Ed25519 private key
   - `DB_HOST` ← `terraform output -raw mysql_private_host`
   - `DB_PORT` ← `terraform output -raw mysql_port`
   - `DB_NAME` ← `terraform output -raw mysql_database`
   - `DB_USER` ← `terraform output -raw mysql_user`
   - `DB_PASSWORD` ← `terraform output -raw mysql_password`
   - `DB_SSL_CA` ← `terraform output -raw mysql_ca_certificate | base64`

2. Push to `main` → GitHub Actions runs lint → test → build-push → deploy

3. Verify: `curl http://<load_balancer_ip>/healthz` returns `{"status": "ok"}`

---

## 9. Cost Estimate (fra1, May 2026)

| Resource                           | Monthly cost   |
| ---------------------------------- | -------------- |
| 2 × App Droplet s-1vcpu-1gb        | ~$12           |
| 1 × Monitoring Droplet s-1vcpu-2gb | ~$12           |
| Load Balancer                      | ~$12           |
| Managed Valkey db-s-1vcpu-1gb      | ~$15           |
| Managed MySQL db-s-1vcpu-1gb       | ~$15           |
| **Total**                          | **~$66/month** |
