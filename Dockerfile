# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — builder
#   Installa le dipendenze in un virtualenv isolato.
#   Usiamo uno stage separato così nell'immagine finale non finiscono
#   né pip né cache di build.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# 1. Copia prima solo requirements → layer cacheable.
#    Docker lo riutilizza finché requirements.txt non cambia.
COPY app/requirements.txt .

# 2. Crea il virtualenv e installa le dipendenze.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip --quiet \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — runtime
#   Immagine finale: solo Python + venv già pronto + codice app.
#   Niente pip, niente build tools → immagine più piccola e più sicura.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Best practice: non girare mai come root in produzione
RUN groupadd --system appgroup \
    && useradd  --system --gid appgroup appuser

# WORKDIR /srv: l'app vive in /srv/app/ come PACKAGE Python.
# Il file app.py contiene `from app.db import ...`, quindi `app` deve essere
# un package importabile (cartella con __init__.py), non un modulo top-level.
# Con WORKDIR=/srv e codice in /srv/app/, gunicorn risolve `app.app:app`
# come "package app -> modulo app -> oggetto app" e gli import interni
# `from app.db import ...` funzionano correttamente.
WORKDIR /srv

# Copia il venv già compilato dallo stage builder
COPY --from=builder /opt/venv /opt/venv

# Copia il codice applicativo come SOTTOdirectory (preserva il package layout)
COPY --chown=appuser:appgroup app/ ./app/

# Aggiungi il venv al PATH.
# DB_SSL_CA punta al path *dentro al container* dove docker-compose.prod.yml
# monta in read-only il certificato CA del Managed MySQL. Per dev locale
# (mysql:8 senza TLS) il file non esiste e l'app cade in fallback no-TLS.
# FLASK_APP=app.app: punta al modulo `app` dentro al package `app` (per
# `flask run` in dev — gunicorn usa la CMD esplicita sotto).
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_SSL_CA=/etc/mysql-ca/mysql-ca.pem \
    FLASK_APP=app.app

# Porta esposta (documentativa — non fa il publish di per sé)
EXPOSE 5000

USER appuser

# Healthcheck: Docker verifica che il container sia davvero "healthy"
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')"

# Entrypoint: gunicorn in produzione (non il dev server Flask).
# `app.app:app` significa: package `app` -> modulo `app.py` -> oggetto `app`
# (l'istanza Flask creata in app/app.py).
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app.app:app"]

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 3 — dev
#   Estende runtime aggiungendo tool di sviluppo (ruff, mypy, ecc.)
#   Usato solo in locale tramite docker-compose.override.yml
# ─────────────────────────────────────────────────────────────────────────────
FROM runtime AS dev

USER root

# Copia requirements di test/dev
COPY requirements-test.txt /tmp/

# Installa tool di sviluppo nel venv già esistente
RUN pip install --no-cache-dir -r /tmp/requirements-test.txt

# Torna a utente non root
USER appuser