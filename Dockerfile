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

WORKDIR /app

# Copia il venv già compilato dallo stage builder
COPY --from=builder /opt/venv /opt/venv

# Copia il codice applicativo (già di proprietà di appuser → no PermissionError)
COPY --chown=appuser:appgroup app/ .

# Volume per il database SQLite persistente
RUN mkdir -p /data && chown appuser:appgroup /data
VOLUME ["/data"]

# Aggiungi il venv al PATH
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATABASE_PATH=/data/todos.db \
    FLASK_APP=app.py

# Porta esposta (documentativa — non fa il publish di per sé)
EXPOSE 5000

USER appuser

# Healthcheck: Docker verifica che il container sia davvero "healthy"
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/healthz')"

# Entrypoint: gunicorn in produzione (non il dev server Flask)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]