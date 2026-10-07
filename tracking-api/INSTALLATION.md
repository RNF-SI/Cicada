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
# E-mails de l'adhésion au hub (demandes, codes de confirmation, formulaire de contact)
RNF_CONTACT_EMAIL=si@rnfrance.org
ADMIN_BASE_URL=https://tracking.cicada.reserves-naturelles.org
EMAIL_HOST=<serveur SMTP>
EMAIL_PORT=587
EMAIL_HOST_USER=<compte SMTP>
EMAIL_HOST_PASSWORD=<mot de passe SMTP>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=noreply@cicada.reserves-naturelles.org
```

À chaque release, mettre `LATEST_VERSION` à jour puis redémarrer le service.

#### Adhésions au hub (`HUB_URL`, `HUB_ADMIN_TOKEN`)

Une structure demande l'adhésion à l'exploration nationale depuis son instance (Administration > Paramètres >
Exploration fédérée), en indiquant un contact (nom, e-mail, téléphone facultatif, message). La demande arrive dans
l'admin Django (**Instances > Adhésions au hub**) ; un e-mail la signale à `RNF_CONTACT_EMAIL` et un accusé de
réception part au contact.

1. **Prendre contact** avec l'administrateur de la structure et vérifier que la demande émane bien d'elle.
2. Vérifier l'**adresse d'envoi du code** dans la fiche (pré-remplie avec l'e-mail du contact) : de préférence une
   adresse que RNF connaît déjà, et non seulement celle déclarée dans la demande. La corriger et enregistrer si
   besoin.
3. Action **« Envoyer le code de confirmation »** : un code aléatoire (`ABCD-EFGH`, valable 7 jours) part par
   e-mail à cette adresse ; la demande passe en « Code envoyé ». Le code n'est affiché nulle part ailleurs et n'est
   conservé qu'en empreinte. Si l'e-mail ne part pas, l'erreur s'affiche et rien ne change. Renvoyer un code
   invalide le précédent.
4. L'administrateur saisit le code sur son instance. **Un code juste vaut acceptation** : l'API de suivi enrôle
   aussitôt l'instance sur le hub (`POST {HUB_URL}/api/federation/enrolements/`, en-tête `X-Hub-Admin-Token`), avec
   les seules empreintes des jetons de l'instance — les jetons ne la quittent jamais. Si le hub refuse ou est
   injoignable, le code reste valable et l'administrateur réessaie plus tard. Après 5 saisies erronées, le code est
   invalidé et la demande repasse en attente : en renvoyer un.

Il n'y a pas d'action « Accepter » : RNF décide en envoyant le code. **Refuser** : saisir d'abord le motif dans la
fiche (il est affiché à la structure), puis lancer l'action ; un code déjà envoyé cesse alors de valoir.

`HUB_ADMIN_TOKEN` est tiré une fois (`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`) et recopié
à l'identique dans le `.env` du hub et dans celui-ci. Il permet d'enrôler n'importe quelle instance : ne le
transmettez à personne et ne le journalisez pas. Vides, ces deux variables empêchent l'envoi d'un code (il ne
pourrait de toute façon pas aboutir).

#### E-mails (`RNF_CONTACT_EMAIL`, `ADMIN_BASE_URL`, `EMAIL_*`)

| Variable | Défaut | Rôle |
|---|---|---|
| `RNF_CONTACT_EMAIL` | `si@rnfrance.org` | reçoit les nouvelles demandes d'adhésion et les messages du formulaire « Contacter RNF » des instances (`Reply-To` = l'expéditeur) |
| `ADMIN_BASE_URL` | `https://tracking.cicada.reserves-naturelles.org` | adresse publique de cette API de suivi : préfixe du lien vers la fiche de la demande (`/admin/instances/adhesionhub/<id>/change/`) dans l'e-mail à RNF. À changer pour une API de suivi de staging |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | `localhost`, `587`, vide, vide, `True` | serveur SMTP |
| `DEFAULT_FROM_EMAIL` | `noreply@cicada.reserves-naturelles.org` | expéditeur |
| `EMAIL_BACKEND` | SMTP | `django.core.mail.backends.console.EmailBackend` pour tester sans serveur |

Les e-mails partent pendant la requête (délai `EMAIL_TIMEOUT`, 10 s). Un échec d'envoi à la demande d'adhésion est
journalisé sans la faire échouer ; un échec du formulaire de contact est renvoyé à l'instance (502), le message
n'ayant pas d'autre trace.

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
