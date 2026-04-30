# Lezione 2: LB + 2 nodi app + DB self-managed + Managed Valkey

> **Architettura ibrida:** Droplet self-managed dove ha senso didattico (DB con NFS),
> Managed DigitalOcean dove conviene operativamente (cache Valkey).

---

## La struttura della cartella

```
todo-app-infra-v2/
├── .gitignore
├── terraform.tfvars            ← VALORI segreti (gitignored!)
├── terraform.tfvars.example    ← template da copiare
│
├── provider.tf                 ← Terraform + provider DigitalOcean
├── variables.tf                ← dichiarazione delle variabili
├── locals.tf                   ← tag comuni
├── outputs.tf                  ← cosa stampare a fine apply
│
├── project.tf                  ← Project DO + assegnazione resource
├── ssh.tf                      ← chiave SSH
├── network.tf                  ← VPC privata
│
├── droplet-db.tf               ← nodo database self-managed (NFS + SQLite)
├── droplet-app.tf              ← nodi applicativi (×2)
├── load-balancer.tf            ← Load Balancer pubblico
│
├── database-valkey.tf          ← cluster Managed Valkey (NUOVO)
│
├── firewall-app.tf             ← regole firewall nodi app
├── firewall-db.tf              ← regole firewall nodo DB
│
└── cloud-init/
    ├── db.yaml                 ← bootstrap nodo DB (NFS server)
    └── app.yaml                ← bootstrap nodi app (Docker + container)
```

**Cosa è sparito rispetto alla versione "tutto self-managed":**

- ❌ `droplet-cache.tf`
- ❌ `firewall-cache.tf`
- ❌ `cloud-init/cache.yaml`

**Cosa è apparso:**

- ✅ `database-valkey.tf` (cluster Managed Valkey)

---

## Schema dell'infrastruttura

```
                          🌐 Internet
                              │
                              ▼  HTTP :80
                     ┌────────────────┐
                     │ Load Balancer  │  ← unico IP pubblico
                     └────┬───────┬───┘
                          │       │  least-connections verso :5001
       ╔══════════════════│═══════│═══════════════════╗
       ║   VPC privata    ▼       ▼   10.10.10.0/24   ║
       ║   ┌──────────────┐    ┌──────────────┐       ║
       ║   │ App Node 1   │    │ App Node 2   │       ║
       ║   │ Docker:5001  │    │ Docker:5001  │       ║
       ║   │   ↓          │    │   ↓          │       ║
       ║   │ docker-todo  │    │ docker-todo  │       ║
       ║   │ -prod :5000  │    │ -prod :5000  │       ║
       ║   └────┬────┬────┘    └────┬────┬────┘       ║
       ║        │    │              │    │            ║
       ║   NFS  │    │ Valkey  NFS  │    │ Valkey     ║
       ║  :2049 ▼    ▼ :25061 :2049 ▼    ▼ :25061     ║
       ║   ┌──────────────┐    ┌──────────────┐       ║
       ║   │  DB Node     │    │ Managed DB   │       ║
       ║   │  Droplet     │    │ Valkey 8     │       ║
       ║   │  SQLite+NFS  │    │ (DigitalOcean│       ║
       ║   │  self-managed│    │  gestito)    │       ║
       ║   └──────────────┘    └──────────────┘       ║
       ╚═══════════════════════════════════════════════╝
```

**Note importanti:**

- Container Docker: **`docker-todo-prod`** (lo stesso del tuo `docker-compose.prod.yml`)
- Variabile `DATABASE_PATH=/data/todos.db` (con la "s" finale, come nel tuo Dockerfile)
- Health check del LB sul path **`/healthz`**
- **Cache su porta 25061**, non 6379 (i Managed DO usano porte non-standard)
- **Connessione TLS obbligatoria** (`rediss://` con doppia "s") sul Managed Valkey

---

## Perché questa scelta ibrida?

| Componente         | Strategia    | Motivo                                                                                                          |
| ------------------ | ------------ | --------------------------------------------------------------------------------------------------------------- |
| **DB (SQLite)**    | Self-managed | Didatticamente forte: vedi NFS, mount, configurazione manuale                                                   |
| **Cache (Valkey)** | Managed      | Operativamente sensato: backup, patch, password automatici. Su DO l'unica opzione cache managed dal 30/06/2025. |

Questa è la situazione più realistica nelle aziende: si mischiano servizi managed (per scaricare lavoro operativo) e componenti self-hosted (per controllo o costi). Insegna agli studenti che **non è una scelta tutto-o-niente**.

---

## Nota didattica: Redis → Valkey

Su DigitalOcean dal 30 giugno 2025 **non esiste più Managed Redis**. È stato sostituito da Managed Valkey (fork open-source di Redis 7.2.4 sotto BSD pulita, supportato da Linux Foundation).

Per la nostra app Python:

- Il client `redis-py` parla con Valkey **senza modifiche al codice**.
- L'unica differenza pratica: Valkey su DO **richiede TLS e password** (per questo `rediss://` invece di `redis://`).
- Tutta questa complessità è incapsulata in `REDIS_URL`: l'app legge un'unica variabile e tutto funziona.

Per il contesto storico completo di questa transizione, vedi il PDF didattico allegato.

---

## Step 0 — Setup sicuro (invariato)

**0.1** Pannello DO → **Manage → Projects → New Project** → nome: `devops-course`

**0.2** **API → Generate New Token** con custom scopes:

- `droplet`, `ssh_key`, `firewall`, `vpc`, `load_balancer`, `project`, `tag`
- **`database`** ← nuovo, necessario per il cluster Valkey

Scadenza 30 giorni.

> ⚠️ Se stai aggiornando da una versione precedente del corso, devi rigenerare il token per aggiungere lo scope `database`.

**0.3** Sei già nella cartella `infrastructure/`.

---

## Migrazione da Redis self-hosted a Managed Valkey

Se vieni dalla versione precedente con Droplet Redis self-hosted, ecco i passi esatti:

### 1. Rimuovi i file vecchi

```bash
rm droplet-cache.tf       # (o droplet-redis.tf se non rinominato)
rm firewall-cache.tf      # (o firewall-redis.tf)
rm cloud-init/cache.yaml  # (o cloud-init/redis.yaml)
```

### 2. Aggiungi il file nuovo

Crea `database-valkey.tf` (vedi contenuto allegato).

### 3. Aggiorna i 4 file modificati

- `variables.tf` — aggiunte 3 variabili: `cache_engine_version`, `cache_size`, `cache_node_count`
- `project.tf` — assegna `digitalocean_database_cluster.cache.urn` invece di `digitalocean_droplet.cache.urn`
- `droplet-app.tf` — passa `cache_uri` al template invece di `cache_private_ip`
- `outputs.tf` — `cache_host` e `cache_uri` invece di `cache_node_ip`
- `cloud-init/app.yaml` — usa `REDIS_URL` invece di `REDIS_HOST` + `REDIS_PORT`

### 4. Applica

```bash
terraform plan
```

Aspettati di vedere:

```
Plan: 1 to add (database-cluster), 1 to add (database-firewall),
      2 to change (project_resources, app[*]),
      2 to destroy (droplet.cache, firewall.cache).
```

Poi:

```bash
terraform apply
```

⚠️ **Tempo:** la creazione del cluster Valkey richiede **3-5 minuti**. Le Droplet app vengono ricreate (perché cambia il loro `user_data`), altri 3-5 minuti. Totale: **~10 minuti**.

---

## Pre-flight checklist

| #   | Check                           | Come verificare                           |
| --- | ------------------------------- | ----------------------------------------- |
| 1   | Token con scope `database`      | Pannello DO → API                         |
| 2   | Project `devops-course` esiste  | Pannello → Manage → Projects              |
| 3   | App Python supporta `REDIS_URL` | `redis.from_url(os.environ['REDIS_URL'])` |
| 4   | Tutti i file `.tf` ci sono      | `ls -la *.tf cloud-init/`                 |
| 5   | File ASCII puro                 | `file *.tf cloud-init/*.yaml`             |

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
```

Per vedere la connection string del cache:

```bash
terraform output cache_uri
# rediss://default:LA-PASSWORD@devops-course-cache-do-user-xxxxxx-0.b.db.ondigitalocean.com:25061
```

Per testare la connessione cache da un nodo app:

```bash
APP1_IP=$(terraform output -json app_node_ips | jq -r '.[0]')
ssh root@$APP1_IP 'docker exec docker-todo-prod env | grep REDIS_URL'
```

---

## Costi

| Componente                      | Costo/mese |
| ------------------------------- | ---------- |
| 2 × Droplet app (s-1vcpu-1gb)   | ~$12       |
| 1 × Droplet DB (s-1vcpu-1gb)    | ~$6        |
| Load Balancer                   | ~$12       |
| Managed Valkey (db-s-1vcpu-1gb) | ~$15       |
| **Totale**                      | **~$45**   |

vs ~$36 della versione 100% self-managed. **+$9/mese** per non occuparti più di patch, password, backup di Redis.

---

## A fine lezione

```bash
terraform destroy
```

⚠️ I cluster managed ci mettono **2-3 minuti in più** delle Droplet a essere distrutti. Aspetta che `destroy` finisca completamente prima di chiudere il terminale.

---

## Compiti per casa

1. 🥉 **Aggiungi un terzo nodo app** (`count = 3` in `droplet-app.tf`)
2. 🥈 **Migra anche il DB a managed PostgreSQL** (richiede modifica all'app: SQLite → Postgres)
3. 🥇 **Aggiungi un read replica** al cluster Valkey con `node_count = 2`
4. 🏆 **HTTPS sul LB** con certificato Let's Encrypt
5. 🏆🏆 **CD automatico** con GitHub Actions: build immagine → push → deploy sui nodi
