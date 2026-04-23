# 🐳 Docker Todo — Guida CI/CD

Mini todo app in Flask usata come esempio pratico per spiegare
Docker, multi-stage build e CI/CD con GitHub Actions.

---

## Struttura del progetto

```
docker-todo/
├── app/
│   ├── app.py              ← Flask backend + serve il frontend
│   ├── requirements.txt
│   └── templates/
│       └── index.html      ← Frontend vanilla JS
│
├── Dockerfile              ← Multi-stage build (builder + runtime)
├── docker-compose.yml      ← Ambiente di sviluppo locale
├── docker-compose.prod.yml ← Override per produzione
├── .dockerignore
└── .github/
    └── workflows/
        └── ci-cd.yml       ← Pipeline GitHub Actions
```

---

## Avvio locale (senza Docker)

```bash
cd app
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_PATH=/tmp/todos.db flask run
# → http://localhost:5000
```

---

## Avvio con Docker

### Build manuale

```bash
# Build
docker build -t docker-todo .

# Run
docker run -p 5001:5000 -v todo-data:/data docker-todo

# → http://localhost:5000
```

### Con docker compose (dev, hot reload)

```bash
docker compose up --build
# → http://localhost:5000
# Modifica app/app.py → Flask si ricarica automaticamente
```

---

## Concetti Docker mostrati

### 1. Multi-stage build

Il `Dockerfile` ha **due stage**:

| Stage | Scopo |
|-------|-------|
| `builder` | installa pip + dipendenze in un venv |
| `runtime` | copia solo il venv compilato + il codice |

Risultato: l'immagine finale **non contiene pip**, build tools o cache.

```bash
# Verifica dimensione immagine
docker images docker-todo
```

### 2. Layer caching

```dockerfile
COPY requirements.txt .          # ← layer 1: cambia raramente
RUN pip install -r requirements.txt  # ← layer 2: cacheable

COPY app/ .                      # ← layer 3: cambia spesso
```

Regola: **metti prima ciò che cambia meno** → rebuild veloci.

```bash
# Prima build (no cache)
time docker build -t docker-todo .

# Modifica solo app.py, poi rebuild → molto più veloce
touch app/app.py
time docker build -t docker-todo .
```

### 3. Non girare come root

```dockerfile
RUN useradd --system appuser
USER appuser
```

```bash
# Verifica
docker run --rm docker-todo whoami
# → appuser
```

### 4. Healthcheck

```bash
# Vedi lo stato del container
docker inspect --format='{{.State.Health.Status}}' docker-todo-dev

# Output possibili: starting | healthy | unhealthy
```

### 5. Volume per la persistenza

```bash
# I dati sopravvivono al riavvio del container
docker compose down
docker compose up -d
# → i todo sono ancora lì
```

---

## Pipeline CI/CD — GitHub Actions

```
push su main
    │
    ▼
┌─────────┐     ┌──────────────┐     ┌────────┐
│  test   │────▶│ build & push │────▶│ deploy │
│         │     │   su GHCR    │     │  SSH   │
└─────────┘     └──────────────┘     └────────┘

push su PR
    │
    ▼
┌─────────┐
│  test   │  (solo lint + smoke test, no push)
└─────────┘
```

### Secret da configurare nel repo GitHub

```
Settings → Secrets and variables → Actions → New repository secret
```

| Secret | Valore |
|--------|--------|
| `DEPLOY_HOST` | IP o hostname del server |
| `DEPLOY_USER` | es. `ubuntu` |
| `DEPLOY_SSH_KEY` | chiave privata SSH (PEM) |

### Aggiungere la chiave SSH al server

```bash
# Sul tuo PC: genera una coppia di chiavi dedicata al deploy
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_key

# Sul server: aggiungi la chiave pubblica
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys

# In GitHub: aggiungi il contenuto di deploy_key come secret DEPLOY_SSH_KEY
cat ~/.ssh/deploy_key
```

### Setup sul server di produzione

```bash
# Sul server
git clone https://github.com/TUO_USER/docker-todo.git ~/docker-todo

# Login su GHCR (necessario per fare docker pull di immagini private)
echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin
```

---

## Comandi utili per la lezione

```bash
# Ispeziona i layer dell'immagine
docker history docker-todo

# Entra nel container in esecuzione
docker exec -it docker-todo-dev sh

# Vedi i log in tempo reale
docker compose logs -f

# Controlla uso risorse
docker stats

# Vedi i volumi
docker volume ls
docker volume inspect docker-todo_todo-data

# Pulisci tutto (attenzione: cancella anche i volumi!)
docker compose down -v
```
