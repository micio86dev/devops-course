# Da copiare nel file `terraform.tfvars`: file con i VALORI delle variabili.
# Viene letto automaticamente da Terraform a ogni comando.
# IMPORTANTE: aggiunto a .gitignore — contiene segreti, mai su Git!

# Token API copiato dal pannello DigitalOcean → API → Generate New Token
do_token = "dop_v1_xxxxxxxxxxxxxxxxxxxxxxxxxx"

# Contenuto della chiave PUBBLICA (mai la privata!).
# Per ottenerla: cat ~/.ssh/id_ed25519.pub
ssh_public_key = "ssh-ed25519 AAAA... utente@macbook"

# Riferimento completo all'immagine: registry/utente/nome:tag
# "latest" è ok per la lezione, in produzione meglio un tag versionato (v1.0.0)
docker_image = "utente/todo-app:latest"

# ============================================================================
# Variabili per il nodo monitoring (aggiungere in terraform.tfvars)
# ============================================================================

# Path alla chiave SSH privata (per remote-exec su nodi app).
# Default: ~/.ssh/id_ed25519 — da sovrascrivere solo se usi un path diverso.
# ssh_private_key_path = "~/.ssh/id_ed25519"

# Password admin di Grafana — scegliere una password sicura
grafana_password = "una-password-sicura"

# Webhook Slack (lasciare vuoto per disabilitare le notifiche)
# alertmanager_slack_url     = ""
# alertmanager_slack_channel = "#alerts"
