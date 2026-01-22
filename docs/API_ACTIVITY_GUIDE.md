# API Activity - Guide de référence

Ce document décrit l'API REST pour l'historique d'activité (`/api/activity/`).

## Vue d'ensemble

L'API Activity fournit une timeline unifiée des activités, notifications et validations du système. Elle permet aux utilisateurs de suivre l'historique des modifications sur leurs sites, plans et autres entités.

## Authentification

Tous les endpoints requièrent une authentification JWT.

```bash
curl -X GET http://localhost:8000/api/activity/ \
  -H "Authorization: Bearer {access_token}"
```

## Modèle ActivityLog

| Champ | Type | Description |
|-------|------|-------------|
| `id` | integer | Identifiant unique |
| `entity_type` | string | Type d'entité (site, plan, user, organisme, validation) |
| `entity_id` | integer | ID de l'entité concernée |
| `entity_name` | string | Nom de l'entité (dénormalisé) |
| `actor` | FK → Role | Utilisateur ayant effectué l'action (nullable) |
| `actor_name` | string | Nom de l'acteur (dénormalisé, "Système" si null) |
| `action` | string | Type d'action effectuée |
| `description` | text | Description lisible de l'action |
| `related_site` | FK → Site | Site lié (nullable) |
| `related_plan` | FK → PlanGestion | Plan lié (nullable) |
| `related_organisme` | FK → BibOrganismes | Organisme lié (nullable) |
| `related_user` | FK → Role | Utilisateur concerné (nullable) |
| `changes` | JSON | Dict des changements `{field: {old, new}}` |
| `metadata` | JSON | Métadonnées additionnelles |
| `visibility` | string | Niveau de visibilité (public, admin, system) |
| `created_at` | datetime | Date/heure de création |

## Types d'entités

| Type | Description |
|------|-------------|
| `site` | Site / Espace protégé |
| `plan` | Plan de gestion |
| `user` | Utilisateur |
| `organisme` | Organisme gestionnaire |
| `validation` | Demande de validation |

## Types d'actions

| Action | Description |
|--------|-------------|
| `create` | Création d'entité |
| `update` | Modification d'entité |
| `delete` | Suppression d'entité |
| `add_member` | Ajout d'un membre à un site |
| `remove_member` | Retrait d'un membre d'un site |
| `add_referent` | Nomination d'un référent |
| `remove_referent` | Retrait d'un référent |
| `status_change` | Changement de statut |
| `activate` | Activation d'un compte |
| `deactivate` | Désactivation d'un compte |
| `access_granted` | Accès accordé |
| `access_revoked` | Accès révoqué |
| `validation_approved` | Demande approuvée |
| `validation_rejected` | Demande rejetée |
| `rgpd_request` | Demande RGPD de suppression |
| `rgpd_cancelled` | Annulation demande RGPD |
| `rgpd_anonymized` | Compte anonymisé |
| `file_upload` | Upload de fichier |
| `file_delete` | Suppression de fichier |

## Niveaux de visibilité

| Visibilité | Qui peut voir | Description |
|------------|---------------|-------------|
| `public` | Tous les utilisateurs concernés | Activités normales |
| `admin` | admin_og et super_admin | Activités d'administration |
| `system` | super_admin uniquement | Activités système et RGPD |

## Filtrage par rôle

| Rôle | Activités visibles |
|------|-------------------|
| **super_admin** | Toutes les activités (y compris RGPD et système) |
| **admin_og** | Activités de son organisme + sites gérés |
| **référent** | Activités de ses sites et plans |
| **utilisateur** | Activités de ses sites (où il est membre) |

---

## Endpoints

### Liste des activités

```
GET /api/activity/
```

Retourne une liste paginée des activités filtrées selon le rôle de l'utilisateur.

**Paramètres de requête**

| Paramètre | Type | Description |
|-----------|------|-------------|
| `entity_type` | string | Filtrer par type d'entité |
| `action` | string | Filtrer par type d'action |
| `site_id` | integer | Filtrer par site lié |
| `plan_id` | integer | Filtrer par plan lié |
| `since` | ISO datetime | Activités après cette date |
| `search` | string | Recherche textuelle |
| `page` | integer | Numéro de page |
| `page_size` | integer | Taille de page (défaut: 20, max: 100) |

**Exemple de réponse**

```json
{
  "pagination": {
    "count": 42,
    "current_page": 1,
    "total_pages": 3,
    "has_next": true,
    "has_previous": false
  },
  "links": {
    "next": "http://localhost:8000/api/activity/?page=2",
    "previous": null
  },
  "results": [
    {
      "id": 123,
      "entity_type": "site",
      "entity_type_display": "Site",
      "entity_id": 45,
      "entity_name": "Réserve de Camargue",
      "actor_name": "Jean Dupont",
      "action": "update",
      "action_display": "Modification",
      "description": "Site mis à jour",
      "related_site": 45,
      "related_site_name": "Réserve de Camargue",
      "related_plan": null,
      "related_plan_name": null,
      "related_organisme": 12,
      "related_organisme_name": "RNF",
      "related_user": null,
      "related_user_name": null,
      "visibility": "public",
      "created_at": "2026-01-21T14:30:00+01:00"
    }
  ]
}
```

### Détail d'une activité

```
GET /api/activity/{id}/
```

Retourne les détails d'une activité spécifique.

### Activités de mes sites

```
GET /api/activity/my_sites/
```

Retourne uniquement les activités des sites où l'utilisateur est membre ou référent.

### Activités de mes plans

```
GET /api/activity/my_plans/
```

Retourne uniquement les activités des plans où l'utilisateur est référent.

### Activités de mes droits

```
GET /api/activity/my_rights/
```

Retourne les activités où l'utilisateur est le sujet d'un changement de droits ou permissions. Accessible à tous les utilisateurs authentifiés.

**Actions trackées :**
- `add_member` - Ajouté comme membre d'un site
- `remove_member` - Retiré d'un site
- `add_referent` - Nommé référent (site ou plan)
- `remove_referent` - Retiré comme référent
- `activate` - Compte activé
- `deactivate` - Compte désactivé
- `access_granted` - Accès accordé
- `access_revoked` - Accès révoqué
- `validation_approved` - Demande approuvée
- `validation_rejected` - Demande rejetée

**Exemple d'utilisation :** Permet à un utilisateur de voir l'historique des changements de ses propres droits (ex: quand il a été ajouté à un site, nommé référent, etc.).

### Activités de validations

```
GET /api/activity/validations/
```

Retourne les activités liées aux validations. Accessible aux admin_og et super_admin.

### Activités RGPD (super_admin)

```
GET /api/activity/rgpd/
```

Retourne les activités RGPD (demandes de suppression, anonymisations). **Réservé aux super_admin.**

**Réponse 403** si l'utilisateur n'est pas super_admin.

### Activités système (super_admin)

```
GET /api/activity/system/
```

Retourne les activités système (alertes, erreurs, maintenance). **Réservé aux super_admin.**

**Réponse 403** si l'utilisateur n'est pas super_admin.

### Statistiques

```
GET /api/activity/stats/
```

Retourne des statistiques agrégées sur les activités.

**Exemple de réponse**

```json
{
  "total": 1250,
  "by_entity_type": {
    "site": 450,
    "plan": 380,
    "user": 220,
    "organisme": 100,
    "validation": 100
  },
  "by_action": {
    "create": 200,
    "update": 800,
    "delete": 50,
    "add_member": 100,
    "remove_member": 50,
    "other": 50
  },
  "today": 25,
  "this_week": 180,
  "this_month": 450
}
```

### Compteurs par onglet

```
GET /api/activity/tabs_counts/
```

Retourne les compteurs pour chaque onglet de l'interface.

**Exemple de réponse**

```json
{
  "all": 1250,
  "my_sites": 180,
  "my_plans": 95,
  "my_rights": 12,
  "notifications": 42,
  "validations": 15,
  "rgpd": 3,
  "system": 8
}
```

| Clé | Description | Disponibilité |
|-----|-------------|---------------|
| `all` | Toutes les activités visibles | Tous |
| `my_sites` | Activités de mes sites | Tous |
| `my_plans` | Activités de mes plans | Tous |
| `my_rights` | Changements de mes droits | Tous |
| `notifications` | Notifications non lues | Tous |
| `validations` | Activités de validation | admin_og+ |
| `rgpd` | Activités RGPD | super_admin |
| `system` | Activités système | super_admin |

---

## Backend : Service ActivityService

Le service `ActivityService` (`apps/core/services.py`) fournit des méthodes pour enregistrer les activités.

### Méthodes principales

```python
# Méthode générique
ActivityService.log_activity(
    entity_type='site',
    entity_id=123,
    entity_name='Réserve de Camargue',
    action='update',
    actor=user,
    description='Site mis à jour',
    changes={'nom_site': {'old': 'Ancien', 'new': 'Nouveau'}},
    visibility='public'
)

# Raccourcis par type d'entité
ActivityService.log_site_activity(site, 'update', user, 'Site mis à jour', changes={...})
ActivityService.log_plan_activity(plan, 'create', user, 'Plan créé')
ActivityService.log_user_activity(target_user, 'activate', admin, 'Compte activé')
ActivityService.log_organisme_activity(organisme, 'update', admin, 'Organisme modifié')
ActivityService.log_validation_activity(validation, 'validation_approved', admin, 'Demande approuvée')
ActivityService.log_rgpd_activity(user, 'rgpd_request', user, 'Demande de suppression')
ActivityService.log_member_change(site, member, 'add_member', admin, is_referent=True)
ActivityService.log_plan_referent_change(plan, referent, 'add_referent', admin)

# Utilitaire pour détecter les changements
changes = ActivityService.get_model_changes(old_instance, new_data, ['field1', 'field2'])
```

## Backend : Signaux automatiques

Les signaux Django (`apps/core/activity_signals.py`) enregistrent automatiquement les activités lors de certaines opérations :

| Signal | Déclencheur | Activité créée |
|--------|-------------|----------------|
| `post_save` Site | Création/modification de site | `create` ou `update` |
| `pre_delete` Site | Suppression de site | `delete` |
| `post_save` PlanGestion | Création/modification de plan | `create` ou `update` |
| `pre_delete` PlanGestion | Suppression de plan | `delete` |
| `post_save` Role | Activation/désactivation | `activate` ou `deactivate` |
| `post_save` CorRoleSite | Ajout membre site | `add_member` |
| `post_delete` CorRoleSite | Retrait membre site | `remove_member` |
| `m2m_changed` PlanGestion.referents | Ajout/retrait référent plan | `add_referent` ou `remove_referent` |

---

## Tests

Les tests sont dans `tests/apps/core/test_activity.py` (48 tests).

```bash
# Exécuter les tests Activity
docker-compose exec web pytest tests/apps/core/test_activity.py -v

# Tests par catégorie
docker-compose exec web pytest tests/apps/core/test_activity.py -k "TestActivityLogModel" -v
docker-compose exec web pytest tests/apps/core/test_activity.py -k "TestActivityService" -v
docker-compose exec web pytest tests/apps/core/test_activity.py -k "TestActivityAPIEndpoints" -v
docker-compose exec web pytest tests/apps/core/test_activity.py -k "TestActivitySignals" -v
```

### Catégories de tests

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestActivityLogModel` | 11 | Tests du modèle ActivityLog |
| `TestActivityService` | 11 | Tests du service ActivityService |
| `TestActivityAPIEndpoints` | 21 | Tests des endpoints API |
| `TestActivitySignals` | 5 | Tests des signaux automatiques |
