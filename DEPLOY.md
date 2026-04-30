Pattern a tre file: docker-compose.yml (base) + docker-compose.override.yml (dev,  
 auto-caricato) + docker-compose.prod.yml (prod, esplicito).

---

Cosa fare su GitHub Actions per il deploy in produzione

1. Secrets da configurare (Settings → Secrets → Actions)

DEPLOY_HOSTS → IP1,IP2 (dai nodi app — terraform output app_node_ips)  
 DEPLOY_USER → root  
 DEPLOY_SSH_KEY → contenuto integrale della chiave privata Ed25519 (-----BEGIN OPENSSH PRIVATE KEY-----)

Per ricavare gli IP dopo terraform apply:  
 terraform -chdir=infrastructure output -json app_node_ips | jq -r 'join(",")'

2. GitHub Environment production (opzionale ma consigliato)

Settings → Environments → New environment → production  
 Abilita "Required reviewers" con il tuo utente: ogni push a main richiede la tua approvazione manuale prima di deployare. È il gate di sicurezza più efficace per non
deployare accidentalmente in prod.

3. Visibilità dell'immagine su GHCR

Dopo il primo push, vai su github.com/<tuo-utente> → Packages → docker-todo e imposta la visibilità a Public (se il repo è pubblico) oppure aggiungi i nodi app come  
 lettori del package. Altrimenti il docker pull sui nodi fallirà con 403.

In alternativa, nel deploy script aggiungi il login a GHCR:  
 echo ${{ secrets.GITHUB_TOKEN }} | docker login ghcr.io -u ${{ github.actor }} --password-stdin
— ma questo richiede di passare il token via SSH, che è più complesso. Più semplice rendere il package pubblico.

4. Prima esecuzione (ordine delle operazioni)

1. terraform apply # crea infrastruttura, cloud-init prepara i nodi
1. Configura i 3 Secrets GitHub (DEPLOY_HOSTS, DEPLOY_USER, DEPLOY_SSH_KEY)
1. Rendi pubblico il GHCR package (o configura l'accesso)
1. git push origin main # scatta la pipeline: lint → test → build → deploy
1. Verifica: curl http://$(terraform -chdir=infrastructure output -raw load_balancer_ip)/healthz

---

Per aggiungere uno staging environment con Terraform

La struttura raccomandata è creare un secondo workspace Terraform (non un secondo modulo):

# Dalla directory infrastructure/

terraform workspace new staging  
 terraform workspace new production # se non esiste già

Oppure, per una separazione più netta:

infrastructure/  
 ├── environments/  
 │ ├── staging/  
 │ │ └── terraform.tfvars # regione, dimensioni ridotte, nome_prefix=devops-staging
│ └── production/  
 │ └── terraform.tfvars # configurazione prod  
 ├── \*.tf # moduli condivisi (invariati)

Con questa struttura:  
 terraform apply -var-file=environments/staging/terraform.tfvars  
 terraform apply -var-file=environments/production/terraform.tfvars

Le variabili da differenziare per staging:

# environments/staging/terraform.tfvars

name_prefix = "devops-staging"  
 droplet_size = "s-1vcpu-512mb" # più piccolo, meno costoso  
 cache_size = "db-s-1vcpu-1gb"

Nel workflow GitHub Actions, aggiungi un job deploy-staging che si attiva sui branch develop e un deploy-production su main, con secret separati  
 (STAGING_DEPLOY_HOSTS, PROD_DEPLOY_HOSTS). L'environment staging non richiede approvazione manuale, quello production sì.
