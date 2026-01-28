# Configuration Email - CICADA

Ce document décrit la configuration du système d'envoi d'emails pour CICADA.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Application   │────▶│  Serveur SMTP   │────▶│   Boîte mail    │
│ (Django/Celery) │     │ (Mailpit/SMTP)  │     │ (destinataire)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

## Développement local (Mailpit)

En développement, **Mailpit** capture tous les emails sans les envoyer réellement.

### Démarrage

```bash
# Démarrer tous les services (inclut Mailpit)
docker compose up -d

# Ou démarrer uniquement Mailpit
docker compose up -d mailpit
```

### Accès

| Service | URL | Description |
|---------|-----|-------------|
| Interface web | http://localhost:8025 | Voir tous les emails capturés |
| Serveur SMTP | localhost:1025 | Utilisé par Django |

### Utilisation

1. **Ouvrir l'interface Mailpit** : http://localhost:8025
2. **Déclencher un email** dans l'application (inscription, notification, etc.)
3. **Voir l'email** apparaître dans Mailpit

### Test manuel

```bash
# Tester l'envoi d'un email via Django shell
docker compose exec web python manage.py shell -c "
from django.core.mail import send_mail
send_mail(
    'Test Email',
    'Ceci est un test.',
    'noreply@cicada.fr',
    ['test@example.com'],
)
print('Email envoyé! Vérifiez http://localhost:8025')
"
```

### Lancer les tests d'intégration email

Avec Mailpit, les tests peuvent vérifier que les emails sont bien générés :

```bash
# Les tests utilisent automatiquement Mailpit
docker compose exec web pytest tests/apps/notifications/test_email_integration.py -m email_integration -v
```

## Production (Serveur SMTP réel)

En production, configurez un vrai serveur SMTP pour envoyer les emails.

### Variables d'environnement

Créez un fichier `.env` ou configurez ces variables sur votre serveur :

```bash
# Backend SMTP
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

# Serveur SMTP de votre organisation
EMAIL_HOST=smtp.reserves-naturelles.org
EMAIL_PORT=587
EMAIL_USE_TLS=true

# Identifiants SMTP
EMAIL_HOST_USER=noreply@reserves-naturelles.org
EMAIL_HOST_PASSWORD=votre-mot-de-passe

# Adresse d'expédition
DEFAULT_FROM_EMAIL=noreply@cicada.reserves-naturelles.org

# URL du site (pour les liens dans les emails)
SITE_URL=https://cicada.reserves-naturelles.org
```

### Configuration docker compose.prod.yml

```yaml
services:
  web:
    environment:
      - EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
      - EMAIL_HOST=${EMAIL_HOST}
      - EMAIL_PORT=${EMAIL_PORT:-587}
      - EMAIL_USE_TLS=${EMAIL_USE_TLS:-true}
      - EMAIL_HOST_USER=${EMAIL_HOST_USER}
      - EMAIL_HOST_PASSWORD=${EMAIL_HOST_PASSWORD}
      - DEFAULT_FROM_EMAIL=${DEFAULT_FROM_EMAIL:-noreply@cicada.reserves-naturelles.org}
      - SITE_URL=${SITE_URL:-https://cicada.reserves-naturelles.org}

  celery-worker:
    environment:
      # Mêmes variables que web
      - EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
      - EMAIL_HOST=${EMAIL_HOST}
      # ... etc
```

### Serveurs SMTP courants

| Fournisseur | HOST | PORT | TLS |
|-------------|------|------|-----|
| Gmail | smtp.gmail.com | 587 | Oui |
| Outlook/Office 365 | smtp.office365.com | 587 | Oui |
| OVH | ssl0.ovh.net | 587 | Oui |
| SendGrid | smtp.sendgrid.net | 587 | Oui |
| Mailjet | in-v3.mailjet.com | 587 | Oui |

> **Note Gmail** : Utilisez un "mot de passe d'application" (pas votre mot de passe normal).
> Paramètres Google > Sécurité > Mots de passe des applications

### Test de la configuration production

```bash
# Tester l'envoi vers une vraie adresse
docker compose exec web python manage.py shell -c "
from django.core.mail import send_mail
from django.conf import settings
print(f'Backend: {settings.EMAIL_BACKEND}')
print(f'Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
send_mail(
    'Test CICADA Production',
    'Si vous recevez cet email, la configuration SMTP fonctionne.',
    settings.DEFAULT_FROM_EMAIL,
    ['test@reserves-naturelles.org'],
)
print('Email envoyé!')
"
```

## Types d'emails envoyés

| Type | Déclencheur | Template |
|------|-------------|----------|
| Inscription en attente | Nouvel utilisateur s'inscrit | `registration_pending.html` |
| Inscription approuvée | Admin valide l'inscription | `registration_approved.html` |
| Inscription refusée | Admin refuse l'inscription | `registration_rejected.html` |
| Notification générique | Diverses notifications | `notification.html` |

### Templates

Les templates email sont dans : `backend/apps/notifications/templates/emails/`

```
emails/
├── base.html                 # Template de base (header/footer CICADA)
├── notification.html         # Notifications génériques
├── registration_pending.html # Confirmation d'inscription
├── registration_approved.html # Compte validé
└── registration_rejected.html # Inscription refusée
```

## Celery et envoi asynchrone

Les emails sont envoyés de manière asynchrone via Celery pour ne pas bloquer l'application.

### Vérifier que Celery fonctionne

```bash
# Voir les logs du worker Celery
docker compose logs -f celery-worker

# Vérifier les tâches en attente
docker compose exec web python manage.py shell -c "
from config.celery import app
i = app.control.inspect()
print('Active:', i.active())
print('Scheduled:', i.scheduled())
"
```

### Tâches email disponibles

| Tâche | Description |
|-------|-------------|
| `send_notification_email` | Envoie une notification par email |
| `send_registration_pending_email` | Email de confirmation d'inscription |
| `send_registration_approved_email` | Email de validation de compte |
| `send_registration_rejected_email` | Email de refus d'inscription |

## Dépannage

### Les emails n'arrivent pas

1. **Vérifier les logs Celery** :
   ```bash
   docker compose logs celery-worker | grep -i email
   ```

2. **Vérifier la configuration** :
   ```bash
   docker compose exec web python manage.py shell -c "
   from django.conf import settings
   print('EMAIL_BACKEND:', settings.EMAIL_BACKEND)
   print('EMAIL_HOST:', settings.EMAIL_HOST)
   print('EMAIL_PORT:', settings.EMAIL_PORT)
   "
   ```

3. **Tester la connexion SMTP** :
   ```bash
   docker compose exec web python -c "
   import smtplib
   server = smtplib.SMTP('mailpit', 1025)  # ou votre serveur SMTP
   server.set_debuglevel(1)
   server.ehlo()
   print('Connexion OK')
   server.quit()
   "
   ```

### Les emails arrivent dans les spams

- Configurez SPF, DKIM et DMARC sur votre domaine
- Utilisez une adresse d'expéditeur avec le même domaine que le serveur SMTP
- Évitez les mots "spam" dans le contenu

### Mailpit ne reçoit rien

1. Vérifier que Mailpit tourne : `docker compose ps mailpit`
2. Vérifier que Django utilise le bon backend : doit être `smtp.EmailBackend`, pas `console.EmailBackend`
3. Vérifier que `EMAIL_HOST=mailpit` et `EMAIL_PORT=1025`

## Utilisateur de test

Un utilisateur avec une vraie adresse email est créé par le seeder :

```bash
# Créer les données de test
docker compose exec web python manage.py seed_testdata
```

| Email | Usage |
|-------|-------|
| `test@reserves-naturelles.org` | Tests d'envoi réel en production |

Cet utilisateur permet de tester l'envoi d'emails réels vers une boîte mail contrôlée par RNF.
