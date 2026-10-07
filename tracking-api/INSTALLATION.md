# Installation de l'API de suivi CICADA

> L'API de suivi reçoit l'enregistrement et le heartbeat nocturne de chaque instance, et leur annonce la dernière version (`LATEST_VERSION`). Sa place dans l'ensemble : [docs/INFRASTRUCTURE.md](../docs/INFRASTRUCTURE.md). Cette installation est rejouée en VM par le scénario `tracking` de [packaging/vm-bench](../packaging/vm-bench/README.md).

## Prérequis

- Python 3.11+
- PostgreSQL 15+
- Serveur Linux (Debian/Ubuntu recommandé)

## Installation

### 1. Cloner ou copier le projet

```bash
cd /opt  # ou autre répertoire de votre choix
# Copier le dossier tracking-api
```

### 2. Créer un environnement virtuel

```bash
cd tracking-api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration

Créer un fichier `.env` à la racine du projet :

```env
DEBUG=False
SECRET_KEY=<générer-une-clé-secrète>
ALLOWED_HOSTS=tracking.cicada.rnf.fr,localhost
DB_NAME=tracking
DB_USER=tracking_user
DB_PASSWORD=<mot-de-passe-sécurisé>
DB_HOST=localhost
DB_PORT=5432
# Dernière version publiée de CICADA, annoncée aux instances (vide = aucune)
LATEST_VERSION=0.1.49
# Hub d'exploration fédérée : enrôlement des instances dont l'adhésion est acceptée
HUB_URL=https://hub.cicada.reserves-naturelles.org
HUB_ADMIN_TOKEN=<même valeur que HUB_ADMIN_TOKEN dans le .env du hub>
```

À chaque release, mettre `LATEST_VERSION` à jour puis redémarrer le service.

#### Adhésions au hub (`HUB_URL`, `HUB_ADMIN_TOKEN`)

Une structure demande l'adhésion à l'exploration nationale depuis son instance (Administration > Paramètres).
La demande arrive dans l'admin Django (**Instances > Adhésions au hub**) avec un **code de vérification**
(« ABC-DEF ») calculé des deux côtés. **Appelez la structure et comparez ce code de vive voix avant
d'accepter** : c'est ce qui prouve que la demande vient bien d'elle.

- **Accepter et enrôler sur le hub** appelle `POST {HUB_URL}/api/federation/enrolements/` avec l'en-tête
  `X-Hub-Admin-Token`. Seules les empreintes des jetons de l'instance transitent : les jetons ne quittent jamais
  l'instance. Si le hub refuse ou est injoignable, la demande reste en attente et l'erreur s'affiche.
- **Refuser** : saisir d'abord le motif dans la fiche (il est affiché à la structure), puis lancer l'action.
- `HUB_ADMIN_TOKEN` est tiré une fois (`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`) et
  recopié à l'identique dans le `.env` du hub et dans celui-ci. Il permet d'enrôler n'importe quelle instance :
  ne le transmettez à personne et ne le journalisez pas. Vides, ces deux variables désactivent l'acceptation.

### 4. Base de données

```bash
# Créer la base de données PostgreSQL
sudo -u postgres psql
CREATE DATABASE tracking;
CREATE USER tracking_user WITH PASSWORD '<mot-de-passe>';
GRANT ALL PRIVILEGES ON DATABASE tracking TO tracking_user;
GRANT USAGE, CREATE ON SCHEMA public TO tracking_user;
\q

# Appliquer les migrations
python manage.py migrate
```

### 5. Créer un superutilisateur (pour l'admin)

```bash
python manage.py createsuperuser
```

### 6. Collecter les fichiers statiques

```bash
python manage.py collectstatic --noinput
```

### 7. Configuration du serveur web (Gunicorn + Apache)

**Installation de Gunicorn :**

```bash
pip install gunicorn
```

**Service systemd : `/etc/systemd/system/cicada-tracking-api.service`**

```ini
[Unit]
Description=CICADA Tracking API
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/tracking-api
Environment="PATH=/opt/tracking-api/venv/bin"
ExecStart=/opt/tracking-api/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    tracking.wsgi:application

[Install]
WantedBy=multi-user.target
```

**Activer le service :**

```bash
sudo systemctl daemon-reload
sudo systemctl enable cicada-tracking-api
sudo systemctl start cicada-tracking-api
```

**Configuration Apache : `/etc/apache2/sites-available/cicada-tracking-api.conf`**

```apache
<VirtualHost *:80>
    ServerName tracking.cicada.rnf.fr

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    Alias /static /opt/tracking-api/static
    <Directory /opt/tracking-api/static>
        Require all granted
    </Directory>
</VirtualHost>
```

```bash
sudo a2enmod proxy proxy_http
sudo a2ensite cicada-tracking-api
sudo apache2ctl configtest
sudo systemctl reload apache2
```

### 8. HTTPS (recommandé)

```bash
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d tracking.cicada.rnf.fr
```

### 9. Vérification

```bash
# Vérifier que le service tourne
sudo systemctl status cicada-tracking-api

# Tester l'API : un enregistrement d'essai doit répondre 201
# (les autres routes exigent le jeton d'une instance : 403 sans lui, c'est normal)
curl -s -w ' [%{http_code}]\n' -H 'Content-Type: application/json' \
     -d '{"token":"00000000-0000-4000-8000-000000000000","version":"essai"}' \
     http://tracking.cicada.rnf.fr/api/instances/register/
# puis supprimer l'instance d'essai :
sudo -u postgres psql -d tracking -c "DELETE FROM tracking_instances WHERE version = 'essai'"
```

### 10. Mise à jour de l'URL dans CICADA

Une fois l'API déployée, mettre à jour l'URL dans `/etc/cicada/cicada.conf` sur chaque instance :

```ini
[CICADA]
TRACKING_API_URL=https://tracking.cicada.reserves-naturelles.org/api
```

## Maintenance

### Logs

```bash
# Logs de l'application
sudo journalctl -u cicada-tracking-api -f

# Logs Apache
sudo tail -f /var/log/apache2/cicada-tracking-api-access.log
```

### Mise à jour

```bash
cd /opt/tracking-api
source venv/bin/activate
git pull  # ou copier les nouveaux fichiers
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart cicada-tracking-api
```

### Backup de la base de données

```bash
# Backup quotidien (à ajouter dans cron)
pg_dump -U tracking_user tracking > /backup/tracking_$(date +%Y%m%d).sql
```
