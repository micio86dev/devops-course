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
| NET-05  | DB Droplet has a public IP for SSH access only; no HTTP exposure          |

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
| APP-04  | Docker and Docker Compose plugin installed via `get.docker.com` script     |
| APP-05  | NFS share mounted at `/mnt/todo-data` (DB node export) on boot             |
| APP-06  | `/etc/fstab` entry ensures NFS remounts after reboot                       |
| APP-07  | Directory `/root/docker-todo/` exists after provisioning                   |
| APP-08  | `/root/docker-todo/.env.valkey` contains `REDIS_URL=rediss://…` (mode 600) |
| APP-09  | No application container running at provision time — CI/CD deploys the app |

### App node firewall

| Spec ID   | Assertion                                                                         |
| --------- | --------------------------------------------------------------------------------- |
| FW-APP-01 | Inbound SSH (port 22) allowed from 0.0.0.0/0 (needed for CI/CD deploy)            |
| FW-APP-02 | Inbound HTTP (port 5001) allowed **only** from the Load Balancer (tag-based rule) |
| FW-APP-03 | All outbound TCP/UDP allowed (Docker image pulls, NFS, Valkey)                    |
| FW-APP-04 | No other inbound ports open                                                       |

---

## 5. DB Node (NFS server)

| Spec ID | Assertion                                                         |
| ------- | ----------------------------------------------------------------- |
| DB-01   | 1 Droplet: `devops-course-db`; size `s-1vcpu-1gb`                 |
| DB-02   | NFS server exports `/srv/todo-data` to `10.10.10.0/24` (VPC only) |
| DB-03   | Export options: `rw,sync,no_subtree_check,no_root_squash`         |
| DB-04   | Listening on port 2049 (NFSv3)                                    |

### DB node firewall

| Spec ID  | Assertion                                                          |
| -------- | ------------------------------------------------------------------ |
| FW-DB-01 | Inbound SSH (port 22) allowed from 0.0.0.0/0                       |
| FW-DB-02 | Inbound NFS (port 2049) allowed only from VPC CIDR `10.10.10.0/24` |
| FW-DB-03 | No HTTP/HTTPS exposure                                             |

---

## 6. Managed Valkey Cluster

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

## 7. Outputs (post `terraform apply`)

| Output             | Description                                                                     |
| ------------------ | ------------------------------------------------------------------------------- |
| `load_balancer_ip` | Public IP of the LB — set as `DEPLOY_HOSTS` after removing the LB from the list |
| `app_url`          | `http://<lb-ip>` — public URL of the application                                |
| `app_node_ips`     | List of public IPs of app nodes → use as `DEPLOY_HOSTS` in GitHub Secrets       |
| `db_node_ip`       | Public IP of DB node (for SSH debugging)                                        |
| `cache_host`       | Private hostname of Valkey (VPC-only)                                           |
| `cache_uri`        | Full Valkey connection URI (sensitive)                                          |
| `project_name`     | DigitalOcean project the resources belong to                                    |

---

## 8. Bootstrap Flow (cloud-init sequence on app nodes)

```
1. apt update + upgrade
2. Install: ca-certificates, curl, gnupg, nfs-common, netcat-openbsd
3. Install Docker via get.docker.com script
4. Enable and start Docker daemon
5. mkdir -p /mnt/todo-data
6. Wait up to 5 min for NFS server port 2049 (nc probe loop, 60 attempts × 5 s)
7. mount -t nfs <db_private_ip>:/srv/todo-data /mnt/todo-data
8. Add NFS entry to /etc/fstab (survives reboot)
9. mkdir -p /root/docker-todo
10. Write REDIS_URL=<cache_uri> to /root/docker-todo/.env.valkey (mode 600)
```

At this point the node is **ready to receive a CI/CD deploy**. No app container runs yet.

---

## 9. First Deploy Prerequisites

After `terraform apply` succeeds, before the first CD run:

1. Add GitHub Secrets:
   - `DEPLOY_HOSTS` ← `terraform output -json app_node_ips | jq -r 'join(",")'`
   - `DEPLOY_USER` ← `root`
   - `DEPLOY_SSH_KEY` ← contents of your Ed25519 private key

2. Push to `main` → GitHub Actions runs lint → test → build-push → deploy

3. Verify: `curl http://<load_balancer_ip>/healthz` returns `{"status": "ok"}`

---

## 10. Cost Estimate (fra1, April 2026)

| Resource                      | Monthly cost   |
| ----------------------------- | -------------- |
| 2 × App Droplet s-1vcpu-1gb   | ~$12           |
| 1 × DB Droplet s-1vcpu-1gb    | ~$6            |
| Load Balancer                 | ~$12           |
| Managed Valkey db-s-1vcpu-1gb | ~$15           |
| **Total**                     | **~$45/month** |
