# Notifications

### Comment ça marche

Le système de notifications informe les utilisateurs des événements importants, à la fois dans l'application (cloche) et par email.

### Deux canaux de notification

| Canal | Description |
|-------|-------------|
| **In-app** | Une notification apparaît dans la cloche du header |
| **Email** | Un email est envoyé de manière asynchrone (via Celery) |

### Quand une notification est créée

1. Un événement se produit (nouvelle demande de validation, approbation, etc.)
2. Le service `NotificationService` crée un enregistrement en base avec : destinataire, type, titre, message, priorité, liens vers objets concernés
3. Si la priorité est "high" ou "critical", un email est automatiquement mis en file d'attente
4. Celery (tâche en arrière-plan) envoie l'email sans bloquer l'application

### Le polling frontend

L'application Angular interroge le serveur toutes les 30 secondes pour récupérer les nouvelles notifications. Elle utilise un paramètre `since=timestamp` pour ne récupérer que les notifications plus récentes que la dernière vérification.

### Le badge de la cloche (compteur)

Le badge affiché sur la cloche représente la **somme de deux compteurs distincts** :

| Compteur | Ce qu'il compte | Comment il diminue |
|----------|-----------------|-------------------|
| **Notifications non lues** | Nouvelles notifications (validations approuvées, associations, etc.) | Automatiquement quand l'utilisateur ouvre le menu de notifications |
| **Validations en attente** | Demandes de validation à traiter (inscriptions, accès sites, etc.) | Quand l'utilisateur **approuve ou rejette** une demande |

**Exemple :**
- Badge affiche "15"
- L'utilisateur ouvre la cloche → les notifications sont marquées comme lues
- Badge affiche maintenant "5" (les 5 validations en attente restantes)
- L'utilisateur va dans `/administration/validations` et approuve 2 demandes
- Badge affiche "3"

**Important :** Les validations en attente ne sont pas des "notifications" au sens strict. Elles représentent des demandes qui nécessitent une action de l'utilisateur (approuver/rejeter). C'est pourquoi elles ne sont pas marquées comme "lues" à l'ouverture du menu.

### Les signaux Django

Certaines notifications sont créées automatiquement quand des événements se produisent en base de données (via les signaux Django `post_save`, `post_delete`, `m2m_changed`).

### Tableau récapitulatif des notifications

Ce tableau liste **tous les cas** où une notification est envoyée dans l'application.

#### Légende

- **Destinataire** : Qui reçoit la notification
- **Type** : Type technique de la notification (voir modèle `Notification`)
- **Priorité** : `low`, `medium`, `high`, `critical`
- **Email** : ✅ = email automatique, ❌ = in-app uniquement
- **Déclencheur** : Signal Django ou appel de service

#### Notifications de validation

| Événement | Destinataire | Type | Priorité | Email | Déclencheur |
|-----------|--------------|------|----------|:-----:|-------------|
| Nouvelle demande d'inscription | Admin_og de l'organisme OU Super_admin | `validation_request` | high | ✅ | Signal `post_save` sur `ValidationRequest` |
| Inscription approuvée | Nouvel utilisateur | `welcome` + `validation_approved` | high | ✅ | Service `ValidationService.approve_registration()` |
| Inscription rejetée | Demandeur (email direct) | Email uniquement | - | ✅ | Service `ValidationService.reject_request()` |
| Demande d'accès site approuvée | Demandeur | `validation_approved` | high | ✅ | Service `ValidationService.approve_site_access()` |
| Demande d'accès plan approuvée | Demandeur | `validation_approved` | high | ✅ | Service `ValidationService.approve_plan_access()` |
| Demande référent validée | Demandeur | `validation_approved` | high | ✅ | Service `ValidationService.approve_referent_validation()` |
| Demande lien site-organisme approuvée | Admin_og demandeur | `validation_approved` | high | ✅ | Service `ValidationService.approve_site_org_link()` |
| Demande création site approuvée | Créateur du site | `validation_approved` | high | ✅ | Service `ValidationService.approve_site_creation()` |
| Demande invitation organisme approuvée | Admin_og demandeur | `validation_approved` | high | ✅ | Service `ValidationService.approve_invite_org_to_site()` (historique uniquement) |
| Demande invitation utilisateur approuvée | Admin ayant invité | `validation_approved` | high | ✅ | Service `ValidationService.approve_invite_user_to_site()` (historique uniquement) |
| Organisme ajouté à un site (invitation directe) | Admin_og des 2 organismes, référents du site, super_admin | `info` | medium/low | ❌ | Service `NotificationService.notify_site_invitation_done()` |
| Utilisateur ajouté à un site (invitation directe) | Admin_og des 2 organismes, référents du site, super_admin | `info` | medium/low | ❌ | Service `NotificationService.notify_site_invitation_done()` + signal `CorRoleSite` |
| Demande rejetée (tous types) | Demandeur | `validation_rejected` | high | ✅ | Service `ValidationService.reject_request()` |
| Demande déjà traitée par un autre | Autres validateurs | `info` | low | ❌ | Service `NotificationService.notify_other_validators()` |

#### Notifications d'accès modules

| Événement | Destinataire | Type | Priorité | Email | Déclencheur |
|-----------|--------------|------|----------|:-----:|-------------|
| Accès module accordé | Utilisateur ciblé | `validation_approved` | medium | ❌ | ViewSet `ValidationRequestViewSet.grant_module_access()` |
| Accès module révoqué | Utilisateur ciblé | `validation_rejected` | medium | ❌ | ViewSet `ValidationRequestViewSet.revoke_module_access()` |

#### Notifications d'associations

| Événement | Destinataire | Type | Priorité | Email | Déclencheur |
|-----------|--------------|------|----------|:-----:|-------------|
| Utilisateur ajouté à un site | Utilisateur associé | `user_associated_site` | medium | ❌ | Signal `post_save` sur `CorRoleSite` |
| Utilisateur retiré d'un site | Utilisateur retiré | `user_removed_site` | medium | ❌ | Signal `post_delete` sur `CorRoleSite` |
| Utilisateur ajouté comme référent plan | Utilisateur ajouté | `user_associated_plan` | medium | ❌ | Signal `m2m_changed` sur `PlanGestion.referents` |

#### Notifications de statut utilisateur

| Événement | Destinataire | Type | Priorité | Email | Déclencheur |
|-----------|--------------|------|----------|:-----:|-------------|
| Compte désactivé | Utilisateur désactivé | `account_deactivated` | critical | ✅ | Signal `post_save` sur `Role` (changement `active=False`) |
| Compte désactivé (info admin) | Super_admins | `account_deactivated` | high | ✅ | Signal `post_save` sur `Role` |
| Organisme modifié | Utilisateur concerné | `organisme_changed` | high | ❌ | Signal `post_save` sur `Role` (changement `id_organisme`) |

#### Alertes système (tâches périodiques Celery)

| Événement | Destinataire | Type | Priorité | Email | Déclencheur |
|-----------|--------------|------|----------|:-----:|-------------|
| Site orphelin (sans utilisateurs) | Super_admins + Admin_og des organismes gestionnaires | `site_orphaned` | high | ✅ | Signal `post_delete` sur `CorRoleSite` + Tâche Celery quotidienne |
| Organisme sans administrateur | Super_admins | `organisme_no_admin` | critical | ✅ | Tâche Celery quotidienne |

### Types de notifications disponibles

Le modèle `Notification` définit les types suivants :

| Type | Label | Description |
|------|-------|-------------|
| `welcome` | Bienvenue | Notification de bienvenue après inscription approuvée |
| `validation_request` | Demande de validation | Nouvelle demande à traiter |
| `validation_approved` | Validation approuvée | Demande approuvée |
| `validation_rejected` | Validation rejetée | Demande rejetée |
| `user_associated_site` | Utilisateur associé à un site | Ajout à un site |
| `user_associated_plan` | Utilisateur associé à un plan | Ajout comme référent plan |
| `user_removed_site` | Utilisateur retiré d'un site | Retrait d'un site |
| `user_removed_plan` | Utilisateur retiré d'un plan | Retrait comme référent plan |
| `account_deactivated` | Compte désactivé | Compte utilisateur désactivé |
| `account_activated` | Compte activé | Compte utilisateur réactivé |
| `organisme_changed` | Organisme modifié | Changement d'organisme par un admin |
| `site_orphaned` | Site sans utilisateurs | Alerte site orphelin |
| `organisme_no_admin` | Organisme sans administrateur | Alerte absence d'admin_og |
| `system_alert` | Alerte système | Alerte technique |
| `info` | Information | Information générale |

### Niveaux de priorité et envoi d'email

| Priorité | Envoi email automatique | Cas d'usage |
|----------|:-----------------------:|-------------|
| `low` | ❌ | Informations secondaires |
| `medium` | ❌ | Événements normaux (associations) |
| `high` | ✅ | Demandes de validation, approbations |
| `critical` | ✅ | Désactivation de compte, alertes système |

**Règle** : Les notifications avec priorité `high` ou `critical` déclenchent automatiquement l'envoi d'un email via Celery.

### Détection en temps réel (Signaux Django)

Les problèmes critiques sont détectés **immédiatement** via les signaux Django (`apps/users/signals.py`) :

| Événement déclencheur | Signal | Vérification effectuée |
|----------------------|--------|------------------------|
| Un admin_og est rétrogradé/désactivé | `post_save` sur `Role` | L'organisme a-t-il encore un admin_og ? |
| Un admin_og est supprimé | `post_delete` sur `Role` | L'organisme a-t-il encore un admin_og ? |
| Un utilisateur est retiré d'un site | `post_delete` sur `CorRoleSite` | Le site a-t-il encore des utilisateurs ? |
| Un utilisateur lié à des sites est désactivé | `post_save` sur `Role` | Ses sites ont-ils encore des utilisateurs actifs ? |

**Avantages** : Notification immédiate, pas d'attente jusqu'au lendemain matin.

### Tâches Celery Beat (tâches planifiées)

#### Architecture Celery

**Celery** est un gestionnaire de tâches asynchrones qui permet d'exécuter des opérations en arrière-plan (envoi d'emails, traitements longs). **Celery Beat** est le planificateur qui déclenche les tâches périodiques selon un calendrier défini.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Django Web    │────▶│      Redis      │◀────│  Celery Worker  │
│   (Producer)    │     │   (Message      │     │  (Consumer)     │
└─────────────────┘     │    Broker)      │     └─────────────────┘
                        └─────────────────┘
                               ▲
                               │
                        ┌──────┴──────┐
                        │ Celery Beat │
                        │ (Scheduler) │
                        └─────────────┘
```

**Composants** :
- **Redis** : File de messages (broker) entre Django et les workers
- **Celery Worker** : Processus qui exécute les tâches en arrière-plan
- **Celery Beat** : Planificateur qui envoie les tâches périodiques au broker

> **⚠️ Important : Comprendre la différence Worker vs Beat**
>
> | Scénario | Emails | Tâches planifiées | Exemple |
> |----------|--------|-------------------|---------|
> | ✅ Worker + Beat | ✅ Fonctionnent | ✅ Fonctionnent | Production normale |
> | ⚠️ Worker seul | ✅ Fonctionnent | ❌ Ne se déclenchent jamais | Les emails partent mais pas de nettoyage auto |
> | ❌ Beat seul | ❌ Ne partent pas | ❌ Planifiées mais jamais exécutées | Les tâches s'accumulent dans Redis |
> | ❌ Aucun | ❌ Ne partent pas | ❌ Ne fonctionnent pas | Mode dégradé |
>
> **En résumé** :
> - **Celery Worker** = le moteur qui **exécute** toutes les tâches (obligatoire)
> - **Celery Beat** = l'horloge qui **déclenche** les tâches planifiées (optionnel mais recommandé)
>
> Sans Worker, rien ne fonctionne. Sans Beat, seules les tâches déclenchées manuellement par Django (emails) fonctionnent.

#### Démarrage avec Docker

Les services Celery sont inclus dans le `docker compose.yml` et démarrent automatiquement :

```bash
# Démarrer tous les services (Django + Celery Worker + Celery Beat)
docker compose up -d

# Voir les logs du worker
docker compose logs -f celery-worker

# Voir les logs du planificateur
docker compose logs -f celery-beat
```

**Services Docker** :
| Service | Container | Rôle |
|---------|-----------|------|
| `celery-worker` | `cicada_celery_worker` | Exécute les tâches asynchrones |
| `celery-beat` | `cicada_celery_beat` | Planifie les tâches périodiques |

**Démarrage manuel** (si besoin de debug) :
```bash
# Worker seul
docker compose exec web celery -A config worker -l info

# Beat seul
docker compose exec web celery -A config beat -l info
```

**Variables d'environnement Celery** :

| Variable | Description | Valeur par défaut |
|----------|-------------|-------------------|
| `CELERY_BROKER_URL` | URL Redis pour la file de messages | `redis://:redis_password@redis:6379/0` |
| `CELERY_RESULT_BACKEND` | URL Redis pour stocker les résultats | `redis://:redis_password@redis:6379/0` |
| `REDIS_PASSWORD` | Mot de passe Redis (utilisé dans les URLs) | `redis_password` |

**Format de l'URL Redis** : `redis://[:password]@host:port/db`

**Configuration dans `config/settings/base.py`** :
```python
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_TIMEZONE = 'Europe/Paris'
```

> **Note** : Ces variables doivent être définies dans les services `web`, `celery-worker` et `celery-beat` du `docker compose.yml` pour que tous les composants puissent communiquer avec Redis.

#### Liste des tâches planifiées

| Tâche | Fréquence | Heure | Description |
|-------|-----------|-------|-------------|
| `cleanup_old_error_logs` | Quotidienne | 3h00 | Nettoie les logs d'erreurs |
| `cleanup_old_notifications` | Quotidienne | 4h00 | Supprime les notifications lues > 90 jours |
| `cleanup_expired_pending_users` | Quotidienne | 5h00 | Expire les inscriptions en attente > 30 jours |
| `process_deletion_requests` | Quotidienne | 6h00 | Anonymise les comptes (RGPD) après délai de grâce |
| `check_organismes_without_admin` | Hebdomadaire | Lundi 8h00 | Audit des organismes sans admin_og |
| `check_orphaned_sites` | Hebdomadaire | Lundi 8h30 | Audit des sites sans utilisateurs |

#### Détail des tâches

##### 1. `check_organismes_without_admin` (audit hebdomadaire)

**Fichier** : `apps/notifications/tasks.py:231-268`

**Ce qu'elle fait** :
1. Parcourt tous les organismes de la base de données
2. Pour chaque organisme, vérifie s'il existe au moins un `admin_og` actif
3. Si aucun admin_og trouvé → envoie une notification **CRITIQUE** aux super_admins
4. Anti-spam : ne renvoie pas si une notification identique existe dans les 7 derniers jours

**Pourquoi c'est important** : Un organisme sans administrateur ne peut plus :
- Gérer ses utilisateurs
- Valider les demandes d'inscription
- Administrer ses sites

**Note** : La détection en temps réel est assurée par les signaux Django. Cette tâche sert de filet de sécurité.

##### 2. `check_orphaned_sites` (audit hebdomadaire)

**Fichier** : `apps/notifications/tasks.py:193-228`

**Ce qu'elle fait** :
1. Identifie les sites actifs qui n'ont aucun utilisateur dans `CorRoleSite`
2. Notifie les super_admins + les admin_og des organismes gestionnaires du site
3. Anti-spam : pas de doublon dans les 7 jours

**Pourquoi c'est important** : Un site sans utilisateur :
- Ne peut plus être géré
- Ses données peuvent devenir obsolètes
- Aucun référent pour répondre aux demandes d'accès

##### 3. `cleanup_old_notifications` (quotidienne)

**Fichier** : `apps/notifications/tasks.py:271-289`

**Ce qu'elle fait** :
- Supprime les notifications **lues** de plus de 90 jours
- Conserve les notifications non lues indéfiniment

**Objectif** : Éviter l'accumulation de données obsolètes en base.

##### 4. `cleanup_expired_pending_users` (quotidienne)

**Fichier** : `apps/notifications/tasks.py:292-320`

**Ce qu'elle fait** :
1. Identifie les `ValidationRequest` de type `user_registration` en status `pending` depuis plus de 30 jours
2. Passe leur statut à `expired`
3. Supprime les `PendingUser` associés

**Objectif** : Nettoyer les inscriptions abandonnées ou non traitées.

##### 5. `process_deletion_requests` (quotidienne - RGPD)

**Fichier** : `apps/notifications/tasks.py:323-361`

**Ce qu'elle fait** :
1. Identifie les utilisateurs avec `deletion_requested_at` non nul et `is_anonymized=False`
2. Vérifie si le délai de grâce de 30 jours est écoulé (`can_be_anonymized()`)
3. Anonymise le compte : email → `anonymized_X@deleted.local`, nom → "Utilisateur Anonymisé"
4. Notifie les super_admins du nombre de comptes anonymisés

**Conformité RGPD** : Permet aux utilisateurs d'exercer leur droit à l'effacement tout en conservant l'intégrité référentielle des données.

##### 6. `cleanup_old_error_logs` (quotidienne)

**Fichier** : `apps/core/tasks.py`

**Ce qu'elle fait** :
- Supprime les logs d'erreurs de plus de 90 jours
- Supprime les logs acquittés de plus de 30 jours

#### Tâches asynchrones (non planifiées)

Ces tâches sont déclenchées à la demande par le code Django :

| Tâche | Déclencheur | Description |
|-------|-------------|-------------|
| `send_notification_email` | Création de notification avec `send_email=True` | Envoie l'email de notification |
| `send_registration_pending_email` | Nouvelle inscription | Email de confirmation d'inscription |
| `send_registration_approved_email` | Validation d'inscription | Email de bienvenue |
| `send_registration_rejected_email` | Rejet d'inscription | Email de notification de rejet |

**Retry automatique** : Ces tâches ont 3 tentatives avec backoff exponentiel en cas d'échec.

### Protection contre les doublons

Le système inclut une protection contre les notifications en double :
- **Associations site** : Vérification des doublons dans les 30 dernières secondes
- **Sites orphelins** : Maximum une notification par site et par semaine
- **Organismes sans admin** : Maximum une notification par organisme et par semaine

---

---

← [Système de Logs](01-logs.md) | [Index](../FONCTIONNALITES.md) | [Validations](03-validations.md) →
