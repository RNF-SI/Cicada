# Installation de l'API de suivi CICADA

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
```

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

# Tester l'API
curl http://tracking.cicada.rnf.fr/api/instances/version/
```

### 10. Mise à jour de l'URL dans CICADA

Une fois l'API déployée, mettre à jour l'URL dans `/etc/cicada/cicada.conf` sur chaque instance :

```ini
[CICADA]
TRACKING_API_URL=https://tracking.cicada.rnf.fr/api
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
