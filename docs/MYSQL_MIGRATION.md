# Migration: SQLite → DigitalOcean Managed MySQL

> Replaces the self-managed SQLite + NFS data layer with a Managed MySQL 8
> cluster on DigitalOcean. Adopts Flask-SQLAlchemy as the ORM and removes
> SQLite from the app entirely.

---

## 1. Why this change

The original setup put a SQLite file on a self-managed droplet and
NFS-exported it to the two app nodes. It worked for a teaching demo but
has three real problems:

- **Single point of failure** — the SQLite/NFS droplet hosts both the
  data and the export; if it falls over, the whole app stops.
- **No managed backups, no PITR** — recovering from a corruption is a
  filesystem-level scramble.
- **Write contention through NFS** — fine at lesson scale, exactly the
  wrong story to teach for production-grade systems.

DigitalOcean's Managed MySQL gives daily snapshots, point-in-time
recovery, automatic patching, and (with `node_count >= 2`) failover —
the same lesson the Valkey migration already taught for caching.

---

## 2. Architecture after the migration

```
┌────────────────┐       ┌────────────────┐
│  app node 1    │       │  app node 2    │
│  Flask + ORM   │       │  Flask + ORM   │
└──────┬─────────┘       └──────┬─────────┘
       │   mysql+pymysql, TLS, port 25060   │
       ▼                                    ▼
       └──────────► Managed MySQL 8 ◄───────┘
                    (in the same VPC,
                     tag-firewall: devops-course)
```

- App: **Flask 3.1 + Flask-SQLAlchemy 3.x + SQLAlchemy 2.0**, connecting
  via **PyMySQL 1.1**.
- Schema: a single `Todo` model declared in `app/models.py`; the table
  is created idempotently by `db.create_all()` at app startup.
- Connection settings are read from environment variables — no code
  change is needed to point at a different cluster.

---

## 3. Environment variables

| Var           | Required | Default                         | Purpose                                                     |
| ------------- | -------- | ------------------------------- | ----------------------------------------------------------- |
| `DB_HOST`     | yes      | —                               | Managed MySQL hostname (private VPC hostname in production) |
| `DB_PORT`     | no       | `3306`                          | TCP port                                                    |
| `DB_NAME`     | yes      | —                               | Database name                                               |
| `DB_USER`     | yes      | —                               | Application user                                            |
| `DB_PASSWORD` | yes      | —                               | Password                                                    |
| `DB_SSL_CA`   | no       | (Dockerfile sets the prod path) | Path to the PEM CA cert. Empty/missing → no TLS             |

In the deploy pipeline values come from two sources, in this order
(later wins):

1. `/root/docker-todo/.env.mysql` — written by cloud-init from the
   Terraform outputs.
2. GitHub Actions secrets `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER`
   / `DB_PASSWORD` / `DB_SSL_CA` — when set, override the file.
   `DB_SSL_CA` is the **base64-encoded** PEM; the workflow decodes it
   to `/root/docker-todo/mysql-ca.pem` before bringing the container up.

---

## 4. Local development

`docker compose up` works out of the box: the dev override defines a
local `mysql:8` service with a healthcheck and the app waits for it
(`depends_on: condition: service_healthy`). No CA cert and no TLS in
dev — `DB_SSL_CA=""` is the override default in
`docker-compose.override.yml`.

```bash
docker compose up --build
# → app on http://localhost:5001, mysql on 127.0.0.1:3306
```

To wipe the data volume:

```bash
docker compose down -v   # removes mysql-data volume
```

For pytest without rebuilding the app image:

```bash
docker compose up mysql -d        # bring up only the local mysql:8
DB_HOST=127.0.0.1 DB_PORT=3306 DB_NAME=todos \
DB_USER=todoapp DB_PASSWORD=todopw DB_SSL_CA="" \
pytest --cov-fail-under=100
```

If port 3306 conflicts with a host-level mysqld, edit the dev compose
to publish on a free host port (e.g. `"3307:3306"`) and pass
`DB_PORT=3307` to pytest.

---

## 5. Provisioning the cluster (Terraform)

The Terraform additions are scoped to four resources plus six outputs;
nothing existing is removed (the SQLite droplet stays for now — see
§ 9).

```bash
cd infrastructure
terraform fmt -check
terraform validate
terraform plan -refresh=false   # expect: +1 cluster, +1 db, +1 user, +1 firewall
terraform apply
```

Cluster provisioning takes ~3–5 minutes.

After apply:

```bash
terraform output mysql_private_host
terraform output mysql_port
terraform output mysql_database
terraform output mysql_user
terraform output -raw mysql_password         # sensitive
terraform output -raw mysql_ca_certificate   # sensitive (PEM)
```

---

## 6. GitHub secrets

Set in **both** the `staging` and `production` GitHub environments
(Repo → Settings → Environments):

```bash
# Plain-text secrets
gh secret set DB_HOST     -e production --body "$(terraform output -raw mysql_private_host)"
gh secret set DB_PORT     -e production --body "$(terraform output -raw mysql_port)"
gh secret set DB_NAME     -e production --body "$(terraform output -raw mysql_database)"
gh secret set DB_USER     -e production --body "$(terraform output -raw mysql_user)"
gh secret set DB_PASSWORD -e production --body "$(terraform output -raw mysql_password)"

# CA cert: the workflow base64-decodes back to PEM
gh secret set DB_SSL_CA   -e production --body "$(terraform output -raw mysql_ca_certificate | base64)"
```

Repeat for `-e staging`.

---

## 7. Cutover runbook

1. **Provision** the cluster (`terraform apply`).
2. **Set GitHub secrets** as in § 6.
3. **Open a brief read-only window** on the SQLite app (or accept the
   write-loss budget for the cutover).
4. **Run the migration script** from one of the app nodes (any node
   that has `/mnt/todo-data` NFS-mounted):
   ```bash
   ssh root@<app-node-ip>
   cd /root/docker-todo
   . .env.mysql
   DATABASE_PATH=/mnt/todo-data/todo.db \
     python3 /path/to/scripts/sqlite_to_mysql.py --dry-run     # preview
   DATABASE_PATH=/mnt/todo-data/todo.db \
     python3 /path/to/scripts/sqlite_to_mysql.py --truncate    # actual
   ```
   Verify the script reports `OK: row counts consistent`.
5. **Trigger the deploy** by merging to `main`. The pipeline will:
   - decode the CA cert into `/root/docker-todo/mysql-ca.pem`,
   - source `.env.mysql` and let the workflow secrets override,
   - bring the app container up against the cluster.
6. **Smoke-test** on the load balancer IP:
   ```bash
   curl -fsS http://<lb-ip>/healthz
   curl -fsS -X POST -H 'content-type: application/json' \
     -d '{"text":"cutover test"}' http://<lb-ip>/api/todos
   curl -fsS http://<lb-ip>/api/todos
   ```

---

## 8. Rollback

The SQLite droplet and its NFS export are still up; the data file in
`/srv/todo-data/todo.db` was never modified by the migration script.

```bash
git revert <merge-commit-sha>
git push origin main
```

CI redeploys the previous image, which re-mounts `/mnt/todo-data` and
talks to SQLite again. Writes that landed on MySQL after the cutover
are not back-filled — accept the loss or re-run a reverse migration
script against a fresh SQLite copy.

---

## 9. Why the SQLite droplet stays (for now)

This PR is intentionally **additive** on the infrastructure side: the
NFS+SQLite droplet, its firewall, and the `apt install nfs-common`
block in the deploy workflow all stay in place so rollback is one
revert away. A follow-up PR removes them once the cutover is stable
for ≥ 1 week:

- `infrastructure/droplet-db.tf`
- `infrastructure/firewall-db.tf`
- the NFS-related blocks in `infrastructure/cloud-init/app.yaml`
- the `nfs-common` install + NFS mount steps in `.github/workflows/ci-cd.yml`

---

## 10. Why no Alembic

There is exactly one table. Adopting Alembic now would add a tooling
layer that the project doesn't yet need. When a second table arrives,
introduce Alembic in the same PR and migrate `db.create_all()` to a
proper baseline.
