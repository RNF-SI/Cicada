# Analyse de couverture des tests

**Date** : 9 février 2025
**Scope** : Ensemble de l'application **hors Plans de Gestion** (fonctionnalité en cours de développement)

---

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Backend (pytest)](#backend-pytest)
  - [Points forts](#backend--points-forts)
  - [Inventaire des tests](#backend--inventaire-des-tests)
  - [Lacunes identifiees](#backend--lacunes-identifiées)
- [Frontend unitaires (Jest)](#frontend-unitaires-jest)
  - [Points forts](#frontend-unitaires--points-forts)
  - [Inventaire des tests](#frontend-unitaires--inventaire-des-tests)
  - [Lacunes identifiees](#frontend-unitaires--lacunes-identifiées)
- [Frontend E2E (Playwright)](#frontend-e2e-playwright)
- [Matrice de couverture par module](#matrice-de-couverture-par-module)
- [Recommandations](#recommandations)

---

## Vue d'ensemble

| Stack | Framework | Tests | Couverture |
|-------|-----------|-------|------------|
| Backend | pytest + pytest-django + Factory Boy | ~485 | ~56% (lignes) |
| Frontend unitaires | Jest + jest-preset-angular | ~1 139 | ~86% des modules |
| Frontend E2E | Playwright | ~156 | Workflows critiques |
| **Total** | | **~1 780** | |

---

## Backend (pytest)

### Backend — Points forts

| Module | Tests | Type | Statut |
|--------|-------|------|--------|
| Users (models, permissions, decorators, middleware) | 148 | Unitaires | Excellent |
| Users API (CRUD, filtres, RGPD) | 74 | Integration | Excellent |
| Notifications (services, views, tasks, models) | 171 | Unitaires | Excellent |
| Notifications API (validations) | 10 | Integration | Correct |
| Core Activity (model, service, API, signals) | 48 | Unitaires | Correct |
| Authentication API (login, refresh, logout, impersonation) | 34 | Integration | Complet |
| Bulk Import (upload, mapping, doublons) | 27 | Integration | Correct |
| Site Duplicates (INPN, noms similaires) | 16 | Integration | Correct |
| Site-Org Unlink | 16 | Integration | Correct |
| Settings API | 17 | Integration | Correct |

### Backend — Inventaire des tests

#### Tests unitaires par app

**App Users (148 tests)**

| Fichier | Tests | Couverture |
|---------|-------|------------|
| `tests/apps/users/test_models.py` | 53 | Role, BibOrganismes, Site, CorRoleSite, CorOgSite |
| `tests/apps/users/test_permissions.py` | 42 | 8 classes de permissions DRF |
| `tests/apps/users/test_decorators.py` | 28 | 6 decorators de protection de vues |
| `tests/apps/users/test_middleware.py` | 25 | 3 middlewares custom (headers, permissions, audit) |

**App Notifications (171 tests)**

| Fichier | Tests | Couverture |
|---------|-------|------------|
| `tests/apps/notifications/test_services.py` | 60 | NotificationService, ValidationService |
| `tests/apps/notifications/test_views.py` | 38 | NotificationViewSet, ValidationRequestViewSet |
| `tests/apps/notifications/test_models.py` | 27 | Notification, ValidationRequest, PendingUser |
| `tests/apps/notifications/test_tasks.py` | 28 | Taches Celery (emails, cleanup) |
| `tests/apps/notifications/test_email_integration.py` | 13 | Templates email + integration Mailpit |
| `tests/apps/notifications/test_signals.py` | 5 | 1 seule classe : TestOrganismeChangeNotification |

**App Core (48 tests)**

| Fichier | Tests | Couverture |
|---------|-------|------------|
| `tests/apps/core/test_activity.py` | 48 | ActivityLog model, ActivityService, API, Signals |

#### Tests d'integration API

| Fichier | Tests | Couverture |
|---------|-------|------------|
| `tests/integration/test_api_users.py` | 74 | RoleViewSet CRUD, pagination, filtres, RGPD |
| `tests/integration/test_api_org_sites.py` | 72 | OrganismeViewSet, SiteViewSet, GeoJSON, doublons |
| `tests/integration/test_api_auth.py` | 34 | Login, refresh, logout, impersonation, stats publiques |
| `tests/integration/test_bulk_import.py` | 27 | Upload, validation, mapping, detection doublons |
| `tests/integration/test_api_settings.py` | 17 | SiteConfigurationView |
| `tests/integration/test_site_duplicates.py` | 16 | Detection doublons INPN et noms similaires |
| `tests/integration/test_api_site_org_unlink.py` | 16 | Deliaison site-organisme |
| `tests/integration/test_api_validations.py` | 10 | Endpoints ValidationRequest |

### Backend — Lacunes identifiées

#### Critique (a tester en priorite)

| Composant | Fichier source | Lignes | Tests existants | Probleme |
|-----------|---------------|--------|-----------------|----------|
| **Users Signals** | `apps/users/signals.py` | ~280 | 5 tests | 7 handlers dont detection sites orphelins et suppression admin quasi non couverts |
| **Notifications Signals** | `apps/notifications/signals.py` | ~150 | 1 classe | 4 handlers sur 5 non testes (`notify_user_site_association`, `notify_user_removed_from_site`, etc.) |
| **Core Middleware** | `apps/core/middleware/logging.py` | ~250 | **0** | Correlation ID, logging requetes, tracking temps de reponse |
| **Core Exception Handler** | `apps/core/exception_handler.py` | ~100 | **0** | Gestion centralisee des erreurs API |
| **Core Logging Handlers** | `apps/core/logging_handlers.py` | ~100 | **0** | Handlers custom de logging |

**Detail des signal handlers non testes :**

Users Signals (5 tests pour 7 handlers) :
- `notify_users_before_organisme_delete()` — pre-delete signal
- `notify_users_before_site_delete()` — pre-delete signal
- `check_organisme_admin_after_role_change()` — post-save role
- `check_organisme_admin_after_role_delete()` — post-delete role
- `check_site_orphaned_after_user_removed()` — post-delete relation
- `check_sites_after_user_deactivation()` — post-save desactivation
- `handle_user_deactivation()` — post-save desactivation

Notifications Signals (1 classe testee sur 5 handlers) :
- `notify_user_site_association()` — NON TESTE
- `check_site_orphaned_on_user_removal()` — NON TESTE
- `notify_user_removed_from_site()` — NON TESTE
- `track_user_deactivation()` — NON TESTE
- `notify_organisme_changed()` — teste (1 classe)

#### Haute priorite

| Composant | Situation |
|-----------|-----------|
| Activity Signals (`apps/core/activity_signals.py`, ~450 lignes) | Couverture partielle dans `test_activity.py`, manque de profondeur |
| Serializer edge cases | Validations d'erreurs et cas limites peu couverts |
| Permissions object-level | Acces au niveau objet teste partiellement |

#### Couverture par composant backend

```
USERS APP:
  Models           ██████████ 100%  (53 tests)
  ViewSets         ██████████ 100%  (74 tests integration)
  Permissions      ██████████ 100%  (42 tests)
  Decorators       ██████████ 100%  (28 tests)
  Middleware       ████████░░  80%  (25 tests, edge cases manquants)
  Signals          ███░░░░░░░  30%  (5 tests pour 7 handlers)
  Filters          █████████░  90%  (couverts en integration)

NOTIFICATIONS APP:
  Models           ██████████ 100%  (27 tests)
  Services         █████████░  95%  (60 tests)
  ViewSets         █████████░  95%  (38 tests)
  Tasks (Celery)   ██████████ 100%  (28 tests)
  Email Templates  █████████░  90%  (13 tests)
  Signals          ██░░░░░░░░  15%  (1 classe testee sur 5 handlers)

CORE APP:
  Models           ██████████ 100%
  ActivityService  █████████░  95%
  Activity Signals █████░░░░░  50%
  Views            █████████░  95%
  Middleware       ░░░░░░░░░░   0%  (AUCUN TEST)
  Logging          ░░░░░░░░░░   0%  (AUCUN TEST)
  Exception Handler░░░░░░░░░░   0%  (AUCUN TEST)

AUTHENTICATION:
  Views/ViewSets   ██████████ 100%  (34 tests)
  Token System     ██████████ 100%
```

---

## Frontend unitaires (Jest)

### Frontend unitaires — Points forts

| Categorie | Specs | Tests | Statut |
|-----------|-------|-------|--------|
| Shared components | 15 | 515 | Excellent |
| Core services | 7 | 227 | Complet |
| Guards et interceptors | 6 | 78 | Complet |
| Feature components (profil, login, register, sites) | 5 | 196 | Bon |

### Frontend unitaires — Inventaire des tests

#### Core Services (7 specs — 227 tests)

| Fichier spec | Tests | Couverture |
|-------------|-------|------------|
| `admin.service.spec.ts` | 59 | Dashboard stats, CRUD organismes/sites/users, doublons |
| `activity.service.spec.ts` | 40 | Logs activite, filtrage, visibilite par role |
| `validation.service.spec.ts` | 32 | Demandes validation, approbation/rejet |
| `auth.service.spec.ts` | 27 | Login, logout, refresh token, roles, impersonation |
| `notification.service.spec.ts` | 22 | Polling, marquage lu, compteur non-lus |
| `logging.service.spec.ts` | 20 | Logging erreurs |
| `settings.service.spec.ts` | 18 | Configuration application |

#### Guards et Interceptors (6 specs — 78 tests)

| Fichier spec | Tests | Couverture |
|-------------|-------|------------|
| `impersonation.interceptor.spec.ts` | 19 | Injection token impersonation |
| `global-error.handler.spec.ts` | 19 | Gestion erreurs et feedback |
| `auth.guard.spec.ts` | 16 | authGuard, roleGuard, adminGuard, guestGuard |
| `impersonation-guard.service.spec.ts` | 13 | Validation etat impersonation |
| `auth.interceptor.spec.ts` | 12 | Injection token, refresh 401 |
| `logging.interceptor.spec.ts` | 12 | Logging requetes/reponses |

#### Feature Components (5 specs — 196 tests)

| Fichier spec | Tests | Couverture |
|-------------|-------|------------|
| `sites-list.component.spec.ts` | 57 | Recherche, filtrage, pagination, creation |
| `site-detail.component.spec.ts` | 57 | Details site, utilisateurs, organisations |
| `register.component.spec.ts` | 49 | Formulaire inscription, validation |
| `profile.component.spec.ts` | 45 | Profil utilisateur, mes demandes, parametres |
| `login.component.spec.ts` | 30 | Formulaire login, erreurs |

#### Shared Components (15 specs — 515 tests)

| Fichier spec | Tests | Couverture |
|-------------|-------|------------|
| `site-form-modal.component.spec.ts` | 55 | Creation/edition site, geometrie, validation |
| `notifications-dialog.component.spec.ts` | 50 | Liste notifications, marquage lu |
| `plan-form-modal.component.spec.ts` | 47 | Creation/edition plan (modale) |
| `access-request-dialog.component.spec.ts` | 45 | Demande acces site/plan |
| `notification-bell.component.spec.ts` | 43 | Badge, compteur non-lus |
| `manage-site-users-modal.component.spec.ts` | 38 | Ajout/retrait membres site |
| `organisme-form-modal.component.spec.ts` | 35 | Formulaire organisme |
| `header.component.spec.ts` | 29 | Navigation, menu utilisateur |
| `admin-role-change-modal.component.spec.ts` | 26 | Promotion/demotion roles |
| `navigation-tile.component.spec.ts` | 23 | Tuiles de navigation |
| `score-icon.component.spec.ts` | 23 | Icones scores (6 niveaux) |
| `delete-account-modal.component.spec.ts` | 23 | Suppression compte |
| `deactivate-user-modal.component.spec.ts` | 21 | Desactivation utilisateur |
| `bulk-site-import-modal.component.spec.ts` | 19 | Import CSV sites |
| `action-icon.component.spec.ts` | 10 | Indicateurs statut actions |

#### Admin Components (1 spec — 24 tests)

| Fichier spec | Tests | Couverture |
|-------------|-------|------------|
| `admin-settings.component.spec.ts` | 24 | Configuration admin |

### Frontend unitaires — Lacunes identifiées

#### Composants feature sans aucun test unitaire (haute priorite)

| Composant | Repertoire | Role |
|-----------|-----------|------|
| `activity.component.ts` | `features/activity/` | Page timeline principale — **fonctionnalite coeur** |
| `admin-validations.component.ts` | `admin/admin-validations/` | Liste des demandes de validation — **workflow admin critique** |
| `validation-detail-dialog.component.ts` | `admin/admin-validations/` | Detail d'une validation |
| `notifications.component.ts` | `features/notifications/` | Page notifications |
| `registration-pending.component.ts` | `features/auth/` | Ecran d'attente inscription |
| `admin-modules.component.ts` | `admin/admin-modules/` | Gestion acces modules |
| `admin-logs.component.ts` | `admin/admin-logs/` | Visualisation logs erreur |

#### Containers admin sans tests (priorite moyenne)

| Composant | Role |
|-----------|------|
| `admin-layout.component.ts` | Wrapper du panneau admin |
| `admin-dashboard.component.ts` | Dashboard admin |
| `admin-users.component.ts` | Container gestion utilisateurs |
| `admin-sites.component.ts` | Container gestion sites |
| `admin-organismes.component.ts` | Container gestion organismes |

#### Modales de liaison sans tests (priorite moyenne)

| Composant | Role |
|-----------|------|
| `link-plan-site-modal.component.ts` | Lier un plan a un site |
| `link-user-site-modal.component.ts` | Ajouter un utilisateur a un site |
| `link-user-organisme-modal.component.ts` | Ajouter un utilisateur a un organisme |
| `link-plan-referent-modal.component.ts` | Assigner un referent a un plan |
| `link-site-organisme-modal.component.ts` | Lier un organisme a un site |
| `find-or-create-site-modal.component.ts` | Recherche/creation de site |
| `remove-user-organisme-modal.component.ts` | Retirer un utilisateur d'un organisme |
| `invite-modal.component.ts` | Invitation utilisateur/organisme |
| `confirm-dialog.component.ts` | Dialogue de confirmation generique |
| `ellipse-icon-button.component.ts` | Bouton icone reutilisable |

#### Composants utilitaires sans tests (priorite basse)

| Composant | Role |
|-----------|------|
| `leaflet-map.component.ts` | Affichage carte PostGIS |
| `leaflet-map-edit.component.ts` | Edition geometrie carte |
| `section-title.component.ts` | Composant titre de page |
| `plan-gauge.component.ts` | Jauge progression plan |
| `view-scope-toggle.component.ts` | Switch perimetre (site/organisme) |
| `module-access-request-dialog.component.ts` | Demande acces module |
| `error-log-detail-dialog.component.ts` | Detail log erreur |

#### Services sans tests (priorite basse)

| Service | Role |
|---------|------|
| `translation.service.ts` | Gestion i18n |
| `public-stats.service.ts` | Statistiques publiques |
| `module.service.ts` | Acces/permissions modules |
| `error-log.service.ts` | API logs erreur |

---

## Frontend E2E (Playwright)

### Inventaire complet

#### Authentication (3 fichiers — 15 tests)

| Fichier | Tests | Scenarios |
|---------|-------|-----------|
| `login.spec.ts` | 5 | Login valide/invalide, champs vides, returnUrl |
| `register.spec.ts` | 7 | Inscription, validation, email doublon |
| `logout.spec.ts` | 3 | Deconnexion, suppression tokens, redirection |

#### Admin (10 fichiers — 51 tests)

| Fichier | Tests | Scenarios |
|---------|-------|-----------|
| `users-list.spec.ts` | 6 | Recherche utilisateurs, filtres, pagination |
| `users-actions.spec.ts` | 5 | Activation/desactivation, assignation site |
| `users-sites.spec.ts` | 4 | Associations sites/plans |
| `sites-list.spec.ts` | 5 | Recherche sites, filtres, pagination |
| `sites-crud.spec.ts` | 5 | Creation site, validation formulaire |
| `sites-orgs.spec.ts` | 3 | Liens organismes/sites |
| `validations.spec.ts` | 6 | Liste validations, filtres |
| `validation-workflow.spec.ts` | 10 | Workflow multi-utilisateurs complet |
| `organismes.spec.ts` | 4 | Grille organismes, detail, recherche |
| `dashboard.spec.ts` | 3 | Statistiques, controle acces |

#### Features (7 fichiers — 68 tests)

| Fichier | Tests | Scenarios |
|---------|-------|-----------|
| `profile.spec.ts` | 18 | Profil, infos utilisateur, RGPD, mes demandes |
| `activity.spec.ts` | 15 | Timeline, onglets par role, filtres, pagination |
| `bulk-import.spec.ts` | 11 | Import en masse, stepper, upload, mapping |
| `impersonation.spec.ts` | 9 | Impersonation admin, banniere, navigation |
| `duplicate-detection.spec.ts` | 8 | Detection doublons INPN et noms similaires |
| `notifications.spec.ts` | 7 | Liste notifications, marquage lu, etat vide |
| `navigation.spec.ts` | 4 | Header, sidebar, liens |

#### Access Control (2 fichiers — 15 tests)

| Fichier | Tests | Scenarios |
|---------|-------|-----------|
| `role-access.spec.ts` | 10 | Controle acces par role (super admin, admin OG, utilisateur) |
| `data-scope.spec.ts` | 5 | Scope donnees par organisme |

### E2E — Note

Les tests E2E **compensent partiellement** les lacunes en tests unitaires frontend, notamment pour :
- `activity.component.ts` — couvert par 15 tests E2E
- `admin-validations.component.ts` — couvert par 16 tests E2E (validations + workflow)
- Admin containers — couverts indirectement par les tests admin

---

## Matrice de couverture par module

| Module fonctionnel | Backend unit | Backend integ | Frontend unit | Frontend E2E | Verdict |
|-------------------|-------------|---------------|---------------|-------------|---------|
| **Authentification** | - | 34 | 109 | 15 | Complet |
| **Utilisateurs** | 148 | 74 | 57 (sites) | 15 (users) | Complet |
| **Organismes** | (dans users) | 72 | 35 (modal) | 4 | Correct |
| **Sites** | (dans users) | 72 + 16 + 16 | 114 (list+detail) | 13 + 8 + 11 | Complet |
| **Notifications** | 171 | 10 | 115 (bell+dialog) | 7 | Complet |
| **Validations** | (dans notif) | 10 | 32 (service) | 16 | Correct |
| **Activite** | 48 | - | 40 (service) | 15 | Composant page non teste |
| **Profil** | - | - | 45 | 18 | Complet |
| **Import masse** | 27 | - | 19 (modal) | 11 | Correct |
| **Impersonation** | (dans auth) | - | 32 (interceptor+guard) | 9 | Complet |
| **Signals backend** | 5 | - | - | - | **CRITIQUE** |
| **Middleware core** | - | - | - | - | **CRITIQUE** |

---

## Recommandations

### Priorite 1 — Critique (impact fiabilite)

**Backend signals et middleware : ~80 tests a ajouter**

| Composant | Tests a creer | Impact |
|-----------|--------------|--------|
| Users Signals (`apps/users/signals.py`) | ~25 tests | Detection sites orphelins, suppression admin, desactivation — logique metier critique |
| Notifications Signals (`apps/notifications/signals.py`) | ~20 tests | 4 handlers non testes : association/retrait site, desactivation |
| Core Middleware (`apps/core/middleware/logging.py`) | ~20 tests | Correlation ID, logging requetes — infrastructure transversale |
| Core Exception Handler | ~10 tests | Gestion centralisee des erreurs |
| Core Logging Handlers | ~5 tests | Handlers custom |

**Fichiers de test a creer :**
```
backend/tests/apps/users/test_signals.py          (NOUVEAU)
backend/tests/apps/core/test_middleware.py         (NOUVEAU)
backend/tests/apps/core/test_exception_handler.py  (NOUVEAU)
backend/tests/apps/core/test_logging.py            (NOUVEAU)
```

**Fichier a enrichir :**
```
backend/tests/apps/notifications/test_signals.py   (1 classe → 5 classes)
```

### Priorite 2 — Haute (qualite code)

**Frontend composants critiques sans tests unitaires**

| Composant | Justification |
|-----------|--------------|
| `activity.component.ts` | Fonctionnalite coeur, logique complexe (onglets, filtres, pagination) |
| `admin-validations.component.ts` | Workflow admin critique (approve/reject) |
| `validation-detail-dialog.component.ts` | Logique d'affichage conditionnelle |

### Priorite 3 — Moyenne (completude)

| Categorie | Elements |
|-----------|----------|
| Admin containers (5 composants) | Layout, dashboard, users, sites, organismes |
| Modales de liaison (10 composants) | Liaison entites, confirmations |
| Activity signals backend | Approfondir test_activity.py |

### Priorite 4 — Basse (nice to have)

| Categorie | Elements |
|-----------|----------|
| Composants carte (Leaflet) | Affichage et edition geometrie |
| Composants utilitaires | Jauges, toggles, titres |
| Services mineurs | Translation, public-stats, error-log |

---

### Estimation d'effort

| Priorite | Tests a ajouter | Effort estime |
|----------|----------------|---------------|
| P1 — Critique | ~80 tests backend | 2-3 jours |
| P2 — Haute | ~50 tests frontend | 1-2 jours |
| P3 — Moyenne | ~80 tests frontend | 2-3 jours |
| P4 — Basse | ~40 tests | 1-2 jours |
| **Total** | **~250 tests** | **6-10 jours** |

**Cible apres correction des lacunes P1+P2 :**
- Backend : ~565 tests (~65% couverture estimee)
- Frontend unitaires : ~1 190 tests
- Total global : ~1 910 tests
