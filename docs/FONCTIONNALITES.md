# Explications fonctionnelles

Ce document explique le fonctionnement des principales fonctionnalités de l'application de manière conceptuelle, sans entrer dans les détails techniques du code.

## Table des matières

| # | Fonctionnalité | Description |
|---|----------------|-------------|
| 1 | [Système de Logs](fonctionnalites/01-logs.md) | Logging, correlation ID, audit |
| 2 | [Notifications](fonctionnalites/02-notifications.md) | In-app, emails, Celery, signaux Django |
| 3 | [Validations](fonctionnalites/03-validations.md) | Workflow de validation, permissions |
| 4 | [Historique d'activité](fonctionnalites/04-activite.md) | Timeline des actions, filtres par rôle |
| 5 | [Impersonnation](fonctionnalites/05-impersonnation.md) | Support utilisateur, audit |
| 6 | [Modules](fonctionnalites/06-modules.md) | Système de modules applicatifs |
| 7 | [Gestion des Sites](fonctionnalites/07-sites.md) | CRUD sites, géométries, doublons INPN |
| 8 | [Pages d'administration](fonctionnalites/08-administration.md) | Users, sites, organismes, validations |
| 9 | [RGPD - Suppression de compte](fonctionnalites/09-rgpd.md) | Droit à l'effacement, anonymisation |
| 10 | [Tests](fonctionnalites/10-tests.md) | pytest, Jest, CI/CD |
| 11 | [Configuration du site](fonctionnalites/11-configuration.md) | Paramètres, image d'accueil |
| 12 | [Page Exploration](fonctionnalites/12-exploration.md) | Page publique vitrine |
| 13 | [Données de test (Seeders)](fonctionnalites/13-seeders.md) ⚠️ | Architecture modulaire des seeders |
| 14 | [Plans de Gestion](fonctionnalites/14-plans.md) | Création, sites en attente, réassignation |
| 15 | [Import en masse de sites](fonctionnalites/15-import-masse.md) | GeoJSON/CSV, validation, doublons, import sync/async |

> ⚠️ = Section réservée aux développeurs

---

## Résumé rapide

### Architecture technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Django 5.0+ / DRF 3.14+ |
| Frontend | Angular 19+ |
| Base de données | PostgreSQL 15+ / PostGIS 3.3+ |
| Tâches async | Celery + Redis |
| Emails | SMTP via Celery |

### Rôles utilisateurs

| Rôle | Niveau | Permissions clés |
|------|--------|------------------|
| `super_admin` | 1 | Accès total, RGPD, configuration |
| `admin_og` | 2 | Gestion de son organisme et ses sites |
| `referent` | 3 | Gestion des sites dont il est référent |
| `utilisateur` | 4 | Consultation, demandes d'accès |

### Types de validation

| Type | Qui peut valider |
|------|------------------|
| `user_registration` | super_admin, admin_og de l'organisme |
| `site_access` | super_admin, admin_og gestionnaire, référent |
| `plan_access` | super_admin, admin_og, référent du plan |
| `referent_validation` | super_admin, admin_og gestionnaire |
| `plan_site_link` | Référents site/plan ou admin_og (selon demandeur) |
| `site_org_link` | super_admin, admin_og des deux organismes |

### Tâches Celery planifiées

| Tâche | Fréquence |
|-------|-----------|
| Nettoyage logs erreurs | Quotidien 3h |
| Nettoyage notifications | Quotidien 4h |
| Expiration inscriptions | Quotidien 5h |
| Anonymisation RGPD | Quotidien 6h |
| Audit organismes sans admin | Hebdo lundi 8h |
| Audit sites orphelins | Hebdo lundi 8h30 |

---

**Historique des mises à jour** :
- Janvier 2026 : Division en fichiers séparés pour meilleure maintenabilité
- Janvier 2026 : Ajout section Données de test (Seeders) - architecture modulaire
- Janvier 2026 : Ajout Configuration du site et Page Exploration
- Janvier 2026 : Ajout fonctionnalité RGPD - Suppression de compte
- Janvier 2026 : Ajout notification `organisme_changed` (changement d'organisme par admin)
- Janvier 2026 : Ajout validation `site_org_unlink` (demande de retrait d'organisme d'un site)
- Janvier 2026 : Ajout import en masse de sites (GeoJSON/CSV, validation, doublons, async Celery)
- Mars 2026 : Ajout validation plan-site link, permissions élargies référents plan, notifications
