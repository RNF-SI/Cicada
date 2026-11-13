# Explications fonctionnelles (développeurs)

Comment fonctionne CICADA, fonctionnalité par fonctionnalité : les règles, les modèles et les fichiers à connaître avant de toucher au code. Pour l'usage écran par écran, voir la **notice** du site de documentation (`documentation/`, servi par chaque instance sous `/aide/`).

> Point d'entrée de toute la documentation : [docs/README.md](README.md).

## Le métier : plans de gestion

| # | Page | En bref |
|---|------|---------|
| 14 | [Plans de gestion](fonctionnalites/14-plans.md) | Statuts, circuit CSRPN, versions et rangs, prolongation, sites et utilisateurs d'un plan |
| 16 | [Arborescence](fonctionnalites/16-arborescence.md) | Enjeux et FCR, objectifs, indicateurs, métriques et grilles de scores |
| 17 | [Actions et programmation](fonctionnalites/17-actions.md) | Types d'action, ventilation du budget et du temps, postes, financeurs |
| 18 | [Suivi, Bilan, planification annuelle](fonctionnalites/18-suivi.md) | Saisie du réalisé, ajustement de l'année, pages de lecture |
| 19 | [Exports et imports](fonctionnalites/19-exports-imports.md) | Qui exporte quoi, règles de calcul communes, classeurs réimportables |
| 20 | [Référentiels versionnés](fonctionnalites/20-referentiels.md) | GestRef, PressRef, TaxRef, HabRef : passage de version, actions à actualiser |
| 12 | [Exploration des données](fonctionnalites/12-exploration.md) | Recherche dans le contenu des plans validés |
| 21 | [Exploration fédérée et hub](fonctionnalites/21-federation.md) | Plusieurs instances, publication, consentement |

## Utilisateurs, droits et administration

| # | Page | En bref |
|---|------|---------|
| 23 | [Rôles et droits](fonctionnalites/23-droits.md) | Qui lit, écrit, saisit le suivi, exporte — et où c'est vérifié |
| 08 | [Pages d'administration](fonctionnalites/08-administration.md) | Pages `/administration/…` et ce que voit chaque rôle |
| 03 | [Validations](fonctionnalites/03-validations.md) | Demandes d'accès et de rattachement, qui valide |
| 07 | [Sites](fonctionnalites/07-sites.md) | Sites, géométries, doublons INPN |
| 15 | [Import en masse de sites](fonctionnalites/15-import-masse.md) | GeoJSON / CSV, contrôle, doublons |
| 05 | [Impersonation](fonctionnalites/05-impersonnation.md) | Voir l'application comme un autre, en lecture seule |
| 09 | [RGPD](fonctionnalites/09-rgpd.md) | Demande de suppression de compte, anonymisation |
| 06 | [Modules](fonctionnalites/06-modules.md) | Accès aux modules applicatifs |

## Vie de l'application

| # | Page | En bref |
|---|------|---------|
| 02 | [Notifications](fonctionnalites/02-notifications.md) | In-app et e-mail, signaux, tâches Celery planifiées |
| 04 | [Historique d'activité](fonctionnalites/04-activite.md) | Journal des actions, visibilité par rôle |
| 01 | [Logs](fonctionnalites/01-logs.md) | Journaux, identifiant de corrélation, audit |
| 11 | [Configuration de l'instance](fonctionnalites/11-configuration.md) | Apparence, CGU, Matomo, API publique, partage |
| 22 | [Mise à jour sûre](fonctionnalites/22-mise-a-jour.md) | Sauvegarde vérifiée, retour arrière automatique |
| 10 | [Tests](fonctionnalites/10-tests.md) | pytest, Jest, Playwright, filets transverses, CI |
| 13 | [Données de test](fonctionnalites/13-seeders.md) | `seed_testdata` et ses seeders |

---

## Résumé rapide

### Pile technique

| Composant | Technologie |
|-----------|-------------|
| Backend | Django 5.2 / Django REST Framework |
| Frontend | Angular 22, Angular Material, design system maison |
| Base de données | PostgreSQL 17 / PostGIS 3.5 |
| Tâches asynchrones | Celery + Redis |
| Documentation | MkDocs Material (`documentation/`) |

### Rôles

| Rôle | Portée |
|------|--------|
| `super_admin` | Toute l'instance |
| `redacteur_principal` | Tous les plans, sites et organismes |
| `admin_og` | Son organisme |
| `utilisateur` | Ses sites et ses plans ; **référent** s'il en est désigné |
| `redacteur` (externe) | Les plans auxquels il a demandé l'accès, jamais les suivis |

Détail : [23. Rôles et droits](fonctionnalites/23-droits.md).

### Règles à ne jamais oublier

- On ne modifie un plan qu'**en brouillon** (#248) ; le suivi se saisit plan validé.
- Budget et temps de travail : une seule source de calcul par côté (`operation-budget.ts`, `services_export_finance.py`).
- La programmation se met à jour **en place** : supprimer puis recréer les années effacerait le suivi.
- Une instance se met à jour **par le bouton** : une reprise de données = une migration.
- Budget, RH, mesures et personnes ne sortent **jamais** vers l'exploration ni le hub.
