# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CICADA** - Web application for managing conservation area management plans, developed for CEN (Conservatoire d'Espaces Naturels) and RNF (Réserves Naturelles de France).

- **Current Status**: Plans de Gestion models implemented, Django admin configured
- **Architecture Documentation**: See `claude.md` for detailed specifications
- **Repository**: https://github.com/RNF-SI/Cicada

## ⚠️ RÈGLE OBLIGATOIRE : Design System

**Pour TOUTE tâche impliquant le frontend (Angular/SCSS), tu DOIS :**

1. **Consulter le Design System** : [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) avant de coder
2. **Respecter les couleurs** : Utiliser UNIQUEMENT les variables SCSS définies, jamais de valeurs hex directes
3. **Respecter la typographie** : Font Nunito, tailles et poids définis dans `_typography.scss`
4. **Respecter les composants** : Boutons, formulaires, chips selon les spécifications Figma
5. **Respecter l'accessibilité WCAG AA** : Combinaisons texte/fond approuvées uniquement

**Liens Figma de référence :** Voir `FIGMA_LINKS.md` (non versionné) ou contacter l'équipe design pour accéder aux maquettes (Couleurs, Boutons, Formulaires, Tableaux, Accordéons, Autres composants, Iconographie).

**Combinaisons texte/fond autorisées (WCAG AA) :**

| Fond | Texte autorisé |
|------|----------------|
| `#025359` (Primary) | Blanc uniquement |
| `#B74D5D` (Terra Cotta) | Blanc uniquement |
| `#04854B` (Succès) | Blanc uniquement |
| `#E12329` (Erreur) | Blanc uniquement |
| `#FEC180` (Jaune) | Noir `#343433` ou Primary `#025359` |
| `#F5B399` (Orange saumon) | Noir `#343433` ou Primary `#025359` |
| `#C0E3CF` (Vert pâle) | Noir `#343433` ou Primary `#025359` |
| Scores (`#FF7579`, `#FA9965`, `#F7D35C`, `#82DB8A`, `#81C9D8`) | Noir `#343433` uniquement |
| Blanc | Primary `#025359`, Noir `#343433`, Gris foncé `#746F6E` |

**NE JAMAIS utiliser :**
- Texte blanc sur fonds clairs (jaune, orange, vert pâle, scores)
- Texte couleur score sur fond blanc (pas assez de contraste)
- `mat.$blue-palette` - utiliser `mat.$cyan-palette`
- Couleurs hex directement - utiliser les variables SCSS

## Technology Stack

### Backend
- Django 5.0+ with Django REST Framework 3.14+
- PostgreSQL 17+ with PostGIS 3.5+ for spatial data
- Python 3.11+
- Celery + Redis for async tasks (email notifications)

### Frontend
- Angular 19+ with TypeScript 5+
- Angular Material for UI components
- Leaflet for interactive maps
- **Design System**: Custom SCSS based on Kit UI CICADA (11/2025)
  - **Source de référence**: `KitUI/` (PNG des maquettes)
  - **Status**: ⚠️ 95% complet
  - **Fichiers SCSS**: 6 fichiers (~3500 lignes)
    - `_variables.scss` - Tokens (couleurs, spacing, typography, breakpoints)
    - `_typography.scss` - Styles typographiques + responsive
    - `_responsive.scss` - **Mixins responsive** (breakpoints, containers, grids)
    - `_material-overrides.scss` - Personnalisation Angular Material
    - `_components.scss` - Composants custom (jauges, tuiles, breadcrumb, etc.)
    - `_filters.scss` - Filtres et pagination
  - **Couleurs**: Conformes Kit UI 11/2025
    - Primary: #025359 (Bleu-vert)
    - Secondary: #FEC180 (Jaune), #F5B399 (Orange saumon), #B74D5D (Terra Cotta), #C0E3CF (Vert pâle)
    - Scores: #FF7579, #FA9965, #F7D35C, #82DB8A, #81C9D8
    - Status: #04854B (Succès), #E12329 (Erreur), #FA9965 (Warning), #81C9D8 (Info)
  - **Font**: Nunito (Google Font)
  - **Accessibilité**: WCAG AA compliant - voir [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) pour les règles détaillées
  - **Responsive**: Mobile, Tablet, Desktop
  - **Icônes**:
    - **Uicons by Flaticon**: CDN intégré (Rounded Regular - `fi-rr-*`)
    - **ScoreIconComponent**: Smileys SVG pour scores (very-bad, bad, neutral, good, very-good, no-data)
    - **ActionIconComponent**: Indicateurs d'actions SVG (planned, planned-realized, planned-partial, realized-unplanned, partial-unplanned)
    - Classes utilitaires: `.icon-xs` à `.icon-xxl`, `.icon-primary`, `.icon-btn`, `.icon-circle`
  - **À compléter**:
    - Zebra striping pour tableaux
    - Badge compteur filtres actifs
    - Composant input +/- (fréquence)

### Règles d'utilisation du Design System (IMPORTANT)

**Ces règles doivent être suivies automatiquement pour tout code Angular/SCSS :**

#### Boutons Angular Material
- **Bouton primaire (action principale)**: `mat-flat-button color="primary"`
  - Fond: `$primary-color` (#025359)
  - Texte: blanc
  - Exemple: `<button mat-flat-button color="primary">Créer</button>`

- **Bouton secondaire (action alternative)**: `mat-stroked-button`
  - Bordure: `$primary-color` (#025359)
  - Texte: `$primary-color` (#025359)
  - Au hover: fond `$primary-color`, texte blanc
  - Exemple: `<button mat-stroked-button>Annuler</button>`

- **Bouton tertiaire (action discrète)**: `mat-button`
  - Texte: `$primary-color` (#025359)
  - Sans bordure ni fond
  - Exemple: `<button mat-button>En savoir plus</button>`

- **Tailles**: Ajouter `.btn-sm` ou `.btn-lg` pour les variantes

#### Couleurs à utiliser
| Usage | Variable SCSS | Hex | Ne pas utiliser |
|-------|---------------|-----|-----------------|
| Actions, titres, liens | `$primary-color` | #025359 | Bleu Material (#3f51b5), autres bleus |
| Accent décoratif | `$secondary-yellow` | #FEC180 | - |
| Warnings visuels | `$secondary-orange-salmon` | #F5B399 | - |
| Erreurs bloquantes | `$error-color` | #E12329 | - |
| Succès | `$success-color` | #04854B | - |
| Texte principal | `$black` | #343433 | #000000 |
| Texte secondaire | `$gray-dark` | #746F6E | - |

#### Modales (MatDialog)
- **Largeur standard**: `width: '1300px', maxWidth: '95vw', maxHeight: '90vh'`
- **Éviter**: `width: '600px'` (trop étroit pour les layouts complexes)

#### Configuration du thème Material (CRITIQUE)
Le thème Angular Material est configuré dans `src/styles.scss`:
- **Palette de base**: `mat.$cyan-palette` (la plus proche de #025359)
- **Tokens CSS personnalisés**: Définis dans `:root` pour forcer #025359
- **NE JAMAIS** utiliser `mat.$blue-palette` ou d'autres palettes bleues
- Les tokens spécifiques aux composants (boutons, checkboxes, etc.) sont définis dans `styles.scss` et `_material-overrides.scss`

**Si les boutons/checkboxes affichent une couleur bleue au lieu de #025359:**
1. Vérifier que le thème utilise `mat.$cyan-palette` (pas `mat.$blue-palette`)
2. Vérifier les tokens CSS dans `:root` de `styles.scss`
3. Les overrides sont dans `_material-overrides.scss`

#### Dans les fichiers SCSS de composants
- Toujours importer: `@import 'variables';`
- Utiliser les variables SCSS, jamais les valeurs hex directement
- **Les couleurs sont gérées globalement** - éviter les overrides `!important` dans les composants
- Si absolument nécessaire, utiliser les tokens CSS Material:
```scss
.my-component {
  --mdc-filled-button-container-color: #{$primary-color};
  --mdc-checkbox-selected-icon-color: #{$primary-color};
}
```

### Composants Angular Réutilisables

Les composants standalone sont dans `frontend/src/app/shared/components/`.

#### `NavigationTileComponent`
**Sélecteur**: `app-navigation-tile`
**Fichiers**: `navigation-tile/`
**Description**: Tuile de navigation avec image de fond, forme de coin arrondi et icône.

```html
<app-navigation-tile
  title="Mes plans de gestion"
  uicon="fi-rr-document"
  link="/plans"
  color="primary"
></app-navigation-tile>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `title` | `string` | `''` | Titre affiché en bas de la tuile |
| `uicon` | `string` | `'fi-rr-folder'` | Icône Flaticon (`fi-rr-*`) ou custom (`custom:icon-name`) |
| `link` | `string` | `'/'` | Route de navigation |
| `color` | `'primary' \| 'salmon' \| 'terra-cotta' \| 'yellow'` | `'primary'` | Couleur de la tuile |

**Assets requis** (dans `assets/images/`):
- `tile-backgrounds/bg-{color}.png` - Fond coloré avec vagues
- `corner-shapes/corner-{color}.png` - Forme de coin avec icône
- `icons/{icon-name}.svg` - Icônes custom (si `uicon` commence par `custom:`)

#### `EllipseIconButtonComponent`
**Sélecteur**: `app-ellipse-icon-button`
**Fichiers**: `ellipse-icon-button/`
**Description**: Bouton ellipse avec icône, configurable en couleur et taille.

```html
<!-- Ellipse primaire avec icône blanche -->
<app-ellipse-icon-button icon="fi-rr-document"></app-ellipse-icon-button>

<!-- Ellipse blanche avec icône primaire, grande -->
<app-ellipse-icon-button
  icon="fi-rr-search"
  ellipseColor="white"
  iconColor="primary"
  size="lg"
></app-ellipse-icon-button>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `icon` | `string` | `'fi-rr-document'` | Classe d'icône Flaticon |
| `ellipseColor` | `EllipseColor` | `'primary'` | Couleur de fond (`primary`, `salmon`, `terra-cotta`, `yellow`, `pale-green`, `white`, `beige`, `gray`, `gray-light`) |
| `iconColor` | `'white' \| 'primary'` | `'white'` | Couleur de l'icône |
| `size` | `'xs' \| 'sm' \| 'md' \| 'lg' \| 'xl'` | `'md'` | Taille de l'ellipse |
| `showBorder` | `boolean` | `true` | Afficher la bordure blanche |
| `showShadow` | `boolean` | `true` | Afficher l'ombre |

#### `ScoreIconComponent`
**Sélecteur**: `app-score-icon`
**Fichiers**: `icons/score-icon.component.*`
**Description**: Icône smiley SVG pour afficher les scores/évaluations.

```html
<app-score-icon level="good" [size]="24"></app-score-icon>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `level` | `'very-bad' \| 'bad' \| 'neutral' \| 'good' \| 'very-good' \| 'no-data'` | `'neutral'` | Niveau de score |
| `size` | `number` | `20` | Taille en pixels |

**Couleurs associées**:
- `very-bad`: #FF7579 (rouge)
- `bad`: #FA9965 (orange)
- `neutral`: #F7D35C (jaune)
- `good`: #82DB8A (vert)
- `very-good`: #81C9D8 (bleu)
- `no-data`: #DADADA (gris)

#### `ActionIconComponent`
**Sélecteur**: `app-action-icon`
**Fichiers**: `icons/action-icon.component.*`
**Description**: Indicateur SVG pour le statut des actions dans les plans de gestion.

```html
<app-action-icon status="planned-realized" [size]="28"></app-action-icon>
```

| Input | Type | Défaut | Description |
|-------|------|--------|-------------|
| `status` | `ActionStatus` | `'planned'` | Statut de l'action |
| `size` | `number` | `28` | Taille en pixels |

**Statuts disponibles**:
- `planned`: Cercle pointillé (action prévue)
- `planned-realized`: Cercle plein + ✓ (prévue et réalisée)
- `planned-partial`: Demi-cercle + ✓ (prévue et partiellement réalisée)
- `realized-unplanned`: Cercle + ✗ (réalisée non prévue)
- `partial-unplanned`: Demi-cercle + ✗ (partiellement réalisée non prévue)

#### `HeaderComponent`
**Sélecteur**: `app-header`
**Fichiers**: `header/`
**Description**: Barre de navigation principale de l'application.

```html
<app-header></app-header>
```

## Common Development Commands

### Project Setup (Current Implementation)

```bash
# Docker setup (recommended)
docker compose up -d

# The setup includes:
# - PostgreSQL with PostGIS
# - Redis for caching
# - Django backend with migrations applied
# - Nomenclatures import (reference data)
# - Static files collection
# Note: Test data is NOT created automatically (use seed_testdata command)
```

### Development

```bash
# Backend (via Docker)
docker compose exec web python manage.py runserver

# Database migrations
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate

# Create superuser
docker compose exec web python create_superuser.py

# Create test data (Django management command)
docker compose exec web python manage.py seed_testdata          # Create all test data
docker compose exec web python manage.py seed_testdata --reset  # Remove test data
docker compose exec web python manage.py seed_testdata --dry-run # Preview changes
docker compose exec web python manage.py seed_testdata --only=users,plans  # Selective seeding

# Import/Update nomenclatures (reference data)
docker compose exec web python import_nomenclatures.py

# Test nomenclatures import
docker compose exec web python test_nomenclatures.py

# Access Django shell
docker compose exec web python manage.py shell
```

### Logging

```bash
# Logs en temps réel (filtrés sur les requêtes et erreurs)
docker compose logs -f web | grep -E "(Request|AUDIT|ERROR)"

# Tous les logs en temps réel
docker compose logs -f web
```

**Configuration des logs** (variables d'environnement) :
- `LOG_LEVEL` : Niveau de log (DEBUG, INFO, WARNING, ERROR) - défaut: INFO
- `LOG_DIR` : Répertoire des logs - défaut: /app/logs
- `LOG_SQL` : Activer les logs SQL (true/false) - défaut: false

**Fichiers de logs** (production uniquement) :
- `django.log` : Logs généraux (rotation 10x10MB)
- `error.log` : Erreurs uniquement
- `audit.log` : Actions utilisateur (POST/PUT/DELETE)

**Correlation ID** : Chaque requête HTTP reçoit un UUID unique (`X-Correlation-ID`) propagé dans tous les logs pour faciliter le debugging.

### ⚠️ Architecture Seeders (Pour Développeurs)

> **Attention** : Cette section concerne l'architecture interne du système de données de test. Réservé aux développeurs.

La commande `seed_testdata` utilise une architecture modulaire avec des seeders indépendants :

```
backend/apps/core/management/commands/
├── seed_testdata.py              # Orchestrateur (~300 lignes)
└── seeders/
    ├── __init__.py               # Registry + validation des dépendances
    ├── base.py                   # Classe abstraite BaseSeeder
    ├── context.py                # SeederContext (partage de données)
    ├── signals.py                # Gestion centralisée des signaux (28)
    ├── modules_seeder.py         # 4 modules
    ├── nomenclatures_seeder.py   # Nomenclatures et types (dont Type document plan)
    ├── groups_seeder.py          # 4 groupes Django
    ├── organismes_seeder.py      # 5 organismes
    ├── sites_seeder.py           # 7 sites avec géométries PostGIS
    ├── users_seeder.py           # 14 utilisateurs
    ├── plans_seeder.py           # 9 plans de gestion + chaînes de versions
    ├── pending_users_seeder.py   # 3 PendingUser
    ├── validation_requests_seeder.py  # 22 demandes de validation
    ├── notifications_seeder.py   # 21+ notifications
    ├── error_logs_seeder.py      # 8 logs d'erreur
    └── activity_logs_seeder.py   # 25+ logs d'activité
```

**Composants clés :**

| Composant | Description |
|-----------|-------------|
| `BaseSeeder` | Classe abstraite avec `seed()`, `reset()`, `get_dry_run_summary()` |
| `SeederContext` | Partage de données entre seeders (`set()`, `get()`, `require()`) |
| `signals_disabled()` | Context manager pour désactiver les 28 signaux pendant le seeding |
| `SEEDER_CLASSES` | Liste ordonnée par dépendances (tri topologique) |

**Graphe de dépendances :**
```
modules, nomenclatures, groups, organismes (indépendants)
    │
    ├── sites (deps: organismes, nomenclatures)
    ├── users (deps: organismes, sites, groups)
    ├── pending_users (deps: organismes)
    ├── plans (deps: users, sites, nomenclatures)
    ├── validation_requests (deps: users, sites, plans, organismes)
    ├── notifications (deps: users, sites, plans, organismes, validation_requests)
    ├── error_logs (deps: users)
    └── activity_logs (deps: users, sites, plans, organismes, validation_requests)
```

**Option `--only` :** Permet un seeding sélectif avec résolution automatique des dépendances.
```bash
# Crée uniquement users et plans (+ leurs dépendances automatiquement)
docker compose exec web python manage.py seed_testdata --only=users,plans
```

**Ajouter un nouveau seeder :**
1. Créer `seeders/mon_seeder.py` héritant de `BaseSeeder`
2. Définir `name` et `dependencies`
3. Implémenter `seed()`, `reset()`, `get_dry_run_summary()`
4. Ajouter la classe dans `SEEDER_CLASSES` de `__init__.py`

### Testing

> **Documentation complète** : Voir [`docs/TESTING.md`](docs/TESTING.md) pour le guide détaillé des tests.

#### Résumé de la couverture

| Stack | Framework | Tests | Couverture |
|-------|-----------|-------|------------|
| Backend | pytest + pytest-django + Factory Boy | 356 | 56% |
| Frontend (unitaires) | Jest + jest-preset-angular | 132 | 7% |
| **Frontend (E2E)** | **Playwright** | **155** | **Admin + Features + Access** |
| **Total** | | **~643** | |

#### Backend (pytest)

```bash
# Via Docker (recommandé)
docker compose exec web pytest tests/

# Avec couverture HTML
docker compose exec web pytest tests/ --cov=apps --cov-report=html

# Tests unitaires uniquement
docker compose exec web pytest tests/ -m unit

# Tests d'intégration uniquement
docker compose exec web pytest tests/ -m integration

# Un fichier spécifique
docker compose exec web pytest tests/integration/test_api_users.py -v

# Un test spécifique
docker compose exec web pytest tests/integration/test_api_users.py::TestUsersListEndpoint -v
```

**Structure des tests backend :**
```
backend/tests/
├── factories/           # Factory Boy (UserFactory, PlanGestionFactory, ActivityLogFactory, etc.)
├── apps/               # Tests unitaires
│   ├── users/          # test_models.py, test_permissions.py, test_middleware.py
│   ├── plans/          # test_views.py, test_filters.py
│   ├── core/           # test_activity.py (45 tests - model, service, API, signals)
│   └── notifications/  # test_email_integration.py (tests envoi email réel)
└── integration/        # Tests API
    ├── test_api_auth.py
    ├── test_api_users.py
    ├── test_api_org_sites.py
    ├── test_api_plans.py
    └── test_site_duplicates.py  # Détection doublons INPN et noms similaires
```

#### Tests d'intégration email (Mailpit)

> **Documentation complète** : Voir [`docs/EMAIL_CONFIGURATION.md`](docs/EMAIL_CONFIGURATION.md)

En développement, **Mailpit** capture tous les emails (interface web : http://localhost:8025).

```bash
# Démarrer les services (inclut Mailpit)
docker compose up -d

# Lancer les tests d'intégration email (utilisent Mailpit automatiquement)
docker compose exec web pytest tests/apps/notifications/test_email_integration.py -m email_integration -v

# Tester manuellement l'envoi d'un email
docker compose exec web python manage.py shell -c "
from django.core.mail import send_mail
send_mail('Test', 'Message de test', 'noreply@cicada.fr', ['test@example.com'])
print('Email envoyé! Voir http://localhost:8025')
"
```

**Tests disponibles (27 tests) :**
- `TestNotificationEmailIntegration` : welcome, validation_request, account_deactivated, site_association
- `TestRegistrationEmailIntegration` : pending, approved, rejected
- `TestFullWorkflowEmailIntegration` : workflow complet inscription, accès site
- `TestEmailTemplatesIntegration` : test des 15 types de notifications

#### Frontend (Jest)

```bash
cd frontend

# Tous les tests
npm test

# Mode watch (développement)
npm run test:watch

# Avec couverture
npm run test:coverage
```

**Tests frontend disponibles :**
- `auth.service.spec.ts` - Login, logout, tokens, rôles, impersonation (27 tests)
- `auth.guard.spec.ts` - authGuard, roleGuard, adminGuard, guestGuard (15 tests)
- `auth.interceptor.spec.ts` - Injection token, refresh 401 (13 tests)
- `deactivate-user-modal.component.spec.ts` - Modal de désactivation utilisateur (21 tests)
- `score-icon.component.spec.ts` - Composant ScoreIcon (22 tests)
- `action-icon.component.spec.ts` - Composant ActionIcon (10 tests)
- `navigation-tile.component.spec.ts` - Composant NavigationTile (24 tests)

#### Frontend E2E (Playwright)

```bash
cd frontend

# Tous les tests E2E (headless)
npm run e2e

# Interface visuelle Playwright
npm run e2e:ui

# Tests visibles dans le navigateur
npm run e2e:headed

# Mode debug
npm run e2e:debug
```

**Prérequis** : Stack Docker en cours (`docker compose up -d`) + données de test (`seed_testdata`).

**Tests E2E disponibles (155 tests) :**

*Authentication & Access:*
- `auth/login.spec.ts` - Login valide/invalide, champs vides, returnUrl (5 tests)
- `auth/logout.spec.ts` - Déconnexion, suppression tokens (3 tests)
- `auth/register.spec.ts` - Inscription, validation, email doublon (5 tests)
- `access/role-access.spec.ts` - Contrôle d'accès par rôle (8 tests)
- `access/data-scope.spec.ts` - Scope données par organisme (5 tests)

*Admin:*
- `admin/users-list.spec.ts` - Liste utilisateurs, recherche, filtres (6 tests)
- `admin/users-actions.spec.ts` - Activation/désactivation, assign site (5 tests)
- `admin/users-sites.spec.ts` - Associations sites/plans (4 tests)
- `admin/sites-list.spec.ts` - Liste sites, recherche, filtres (5 tests)
- `admin/sites-crud.spec.ts` - Création site, validation formulaire (5 tests)
- `admin/sites-orgs.spec.ts` - Liens organismes/sites (3 tests)
- `admin/validations.spec.ts` - Liste, filtres, approbation (6 tests)
- `admin/validation-workflow.spec.ts` - **Workflow multi-utilisateurs** : demande → vue admin → approbation/rejet → vérification (8 tests)
- `admin/organismes.spec.ts` - Grille, détail, recherche (4 tests)
- `admin/dashboard.spec.ts` - Statistiques, accès (3 tests)

*Features:*
- `features/notifications.spec.ts` - Liste notifications, marquer lu, état vide (7 tests)
- `features/activity.spec.ts` - Timeline activité, onglets par rôle, filtres, pagination (20 tests)
- `features/profile.spec.ts` - Page profil, infos utilisateur, RGPD, mes demandes (19 tests)
- `features/bulk-import.spec.ts` - Import en masse sites, stepper, upload, mapping (10 tests)
- `features/duplicate-detection.spec.ts` - Détection doublons INPN et noms similaires (9 tests)
- `features/impersonation.spec.ts` - Impersonation admin, bannière, navigation (9 tests)

*Navigation:*
- `navigation/navigation.spec.ts` - Header, sidebar, liens (4 tests)

#### CI/CD

Les tests s'exécutent automatiquement via GitHub Actions sur chaque push/PR vers `main` ou `develop`, et sur les tags de release `v*`.
Configuration : `.github/workflows/tests.yml`

### Frontend Development

```bash
# Install dependencies
cd frontend && npm install

# Development server
npm start  # http://localhost:4200

# Build for production
npm run build:prod

# Generate component
ng generate component components/my-component

# Generate service
ng generate service services/my-service
```

### Code Quality

```bash
# Backend
black backend/  # Format code
isort backend/  # Sort imports
flake8 backend/  # Lint code

# Frontend
npm run lint
npm run format
```

## High-Level Architecture

### Frontend Architecture

The Angular application follows a modular structure:

- **core module**: Singleton services (auth, API client, interceptors)
- **shared module**: Reusable components, pipes, directives, design system components
- **feature modules**: Plans, users, auth (lazy loaded)
- **State management**: RxJS-based with services as stores
- **Design System**: Voir section "Technology Stack > Frontend" et [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md)

#### Composants SCSS disponibles

**`_variables.scss`** - Tokens de design
- Couleurs: `$primary-color`, `$secondary-yellow`, `$secondary-orange-salmon`, `$secondary-terra-cotta`, `$secondary-pale-green`
- Scores: `$score-very-bad`, `$score-bad`, `$score-neutral`, `$score-good`, `$score-very-good`
- Status: `$success-color`, `$error-color`, `$warning-color`, `$info-color`
- Neutres: `$black`, `$gray-dark`, `$gray`, `$gray-light`, `$gray-lighter`, `$beige`, `$white`
- Spacing: `$spacing-xxs` (4px) → `$spacing-xxl` (48px)
- Border radius: `$border-radius-sm` (4px), `$border-radius-pill` (24px), `$border-radius-round` (50%)

**`_typography.scss`** - Classes typographiques
- Headings: `h1`-`h4`, `.h1`-`.h4`
- Texte: `.subtitle`, `.text-regular`, `.text-bold`, `.text-small`, `.text-mention`
- Liens: `.link-default`, `.link-survol`, `.link-inactif`
- Listes: `.list-custom` (puces personnalisées)
- Couleurs: `.text-primary`, `.text-success`, `.text-error`, `.text-muted`, etc.

**`_material-overrides.scss`** - Angular Material personnalisé
- Boutons: `.btn-sm`, `.btn-lg` (tailles)
- Chips/Tags: `.status-success`, `.status-valide`, `.status-error`, `.status-warning`, `.status-info`, `.status-neutre`
- Chips scores: `.score-very-bad`, `.score-bad`, `.score-neutral`, `.score-good`, `.score-very-good`
- Chips priorité: `.priority-1`, `.priority-2`, `.priority-3`
- Accordéons: `.border-primary`, `.border-secondary`, `.border-success`, `.border-error`

**`_components.scss`** - Composants custom (non Material)
- Jauges: `.gauge`, `.gauge-not-started`, `.gauge-mid-progress`, `.gauge-completed`, `.gauge-exceeded`
- Actions: `.action-indicator`, `.action-planned`, `.action-planned-realized`, `.action-planned-partial`, `.action-realized-unplanned`, `.action-partial-unplanned`
- Scores emoji: `.score-emoji` avec variantes
- Tuiles: `.tile`, `.tile-image`, `.tile-content`, `.tile-title`
- Info blocks: `.info-block`, `.info-block-success`, `.info-block-warning`, `.info-block-error`
- Breadcrumb: `.breadcrumb`, `.breadcrumb-home`, `.breadcrumb-item`
- Barre action: `.action-bar`, `.action-bar.with-sidebar`
- Menu latéral: `.sidebar-menu`, `.sidebar-menu-item`, `.sidebar-menu-item.active`, `.sidebar-menu-item.submenu`
- Listes: `.list-bullets`, `.documents-list`
- Pagination: `.pagination-custom`, `.pagination-custom-btn`
- Contrôles: `.segmented-control`

**`_filters.scss`** - Filtres et recherche
- Panneau filtres: `.filter-panel`, `.filter-panel-horizontal`, `.filter-panel-collapsible`
- Filtres actifs: `.active-filters`, `.filter-chip`
- Sidebar filtres: `.sidebar-filters`
- Barre recherche: `.search-filter-bar`
- Quick filters: `.quick-filters`, `.quick-filter-btn`
- Pagination: `.pagination-container`, `.pagination`, `.page-btn`
- Tri: `.sort-controls`, `.view-switcher`
- Mobile: `.filter-drawer`

**`styles.scss`** - Utilitaires globaux
- Spacing: `.m-{size}`, `.p-{size}`, `.mx-{size}`, `.my-{size}`, `.px-{size}`, `.py-{size}`
- Display: `.d-none`, `.d-flex`, `.d-block`, `.d-grid`
- Flex: `.flex-row`, `.flex-column`, `.justify-content-*`, `.align-items-*`
- Background: `.bg-primary`, `.bg-success`, `.bg-error`, `.bg-score-*`
- Border: `.rounded`, `.rounded-sm`, `.rounded-lg`, `.rounded-circle`
- Shadow: `.shadow-sm`, `.shadow`, `.shadow-lg`

### Django Apps Structure

The backend follows a modular architecture with distinct Django apps:

- **authentication**: JWT auth with djangorestframework-simplejwt, login/logout/refresh endpoints, public registration
- **users**: User management, organizations (bib_organismes), role-based permissions system
- **plans**: Management plans CRUD, multi-site support, file attachments *(API REST complète)*
- **notifications**: Validation requests system, email notifications, Celery async tasks
- **api**: Public API endpoints with token auth *(à venir)*
- **core**: Shared utilities, base models (nomenclatures), common middleware
  - See [docs/NOMENCLATURES.md](docs/NOMENCLATURES.md) for reference data management

### Database Schema Design

The application uses PostgreSQL with PostGIS and follows a multi-schema approach compatible with GeoNature and ODASE.
The application is named **Cicada** (`ccd_` prefix for custom schemas).

1. **utilisateurs schema** (GeoNature compatible): User management
   - `t_roles`: User accounts with email as unique identifier
   - `bib_organismes`: Management organizations
   - `cor_role_ep`: User-Site relationships with permissions
   - Django auth tables (auth_group, auth_permission, etc.)

2. **referentiels schema** (ODASE compatible): Protected areas
   - `t_espace_protege`: Protected areas with PostGIS geometries
   - `cor_ep_og`: Organization-Site relationships

3. **ref_nomenclatures schema** (GeoNature compatible): Reference data
   - `bib_nomenclatures_types`: Nomenclature type definitions
   - `t_nomenclatures`: Reference lists and categories

4. **ref_geo schema** (GeoNature compatible): Geographic references
   - Reserved for future use (administrative boundaries, communes, etc.)

5. **general schema** (ODASE compatible): Management plans
   - `t_plan_gestion`: Management plans
     - `plan_parent_id` FK self → chaîne de versions (plan initial → évaluation → plan révisé)
     - `id_type_document` FK nomenclature → type de document (PLAN_INITIAL, EVAL_MI_PARCOURS, PLAN_REVISE)
   - `cor_ep_pg`: Many-to-many between plans and sites
   - `t_plan_gestion_referents`: Plan referents relationships

6. **fichiers schema** (ODASE compatible): File attachments
   - `t_fichiers`: File attachments for management plans

7. **ccd_commons schema** (Cicada): Common utilities
   - `t_modules`: Application modules
   - `t_impersonation_log`: Admin impersonation audit

8. **ccd_notifications schema** (Cicada): Notifications system
   - `t_notifications`: User notifications
   - `t_validation_requests`: Validation workflow
   - `t_pending_users`: Registration requests

**Database Configuration**:
```python
# search_path configured in settings/base.py
OPTIONS = {
    'options': '-c search_path=utilisateurs,referentiels,ref_nomenclatures,ref_geo,general,fichiers,ccd_commons,ccd_notifications,public'
}
```

## Key Implementation Patterns

### Authentication & Permissions

- **User Roles**: Super Admin > Admin Organisme > Utilisateur
- **Référent** (access level, not a role): User is "referent" if assigned as site referent (`CorRoleSite.referent=True`) or plan referent (`PlanGestion.referents`)
- **Permissions cycle de vie des plans** : Les actions de changement de statut et création d'évaluation sont réservées aux **référents du plan spécifique** (vérifié via `plan.referents.filter(pk=user.pk)`), aux admin_og et super_admin. Permission DRF `IsReferent` + vérification objet dans la vue.
- **Permission Model**: Role-based with hierarchical access and Django groups
- **JWT Implementation**: djangorestframework-simplejwt with 60min access + 7-day refresh tokens
- **Security Middleware**: 3 custom middleware for headers, permissions, and audit
- **API Protection**: All endpoints protected by default except `/api/auth/`
- **Permission check methods**: `user.is_super_admin()`, `user.is_referent()`, `user.can_manage_site(site)`
- **DRF classes**: `IsSuperAdmin`, `IsAdminOrganisme`, `IsReferent`
- **Decorators**: `@require_super_admin`, `@require_admin_organisme`

### Geospatial Handling

- Always use PostGIS for spatial operations
- Store geometries in EPSG:4326, display in EPSG:2154 (Lambert-93)
- Use GeoJSON format for API responses
- Implement spatial indexes for performance

### Multi-tenancy & Relationships

- Management plans can span multiple protected areas
- Users belong to organizations with scoped permissions
- Soft delete for critical data (plans, sites)
- Audit trail for all plan modifications

## Critical Implementation Notes

1. **Database Migrations**: Always create reversible migrations
2. **API Design**: RESTful with consistent naming, pagination for lists > 20 items
3. **Frontend State**: Services as stores pattern, avoid NgRx for V0
4. **Testing**: Voir section "Testing" pour les détails. CI/CD via GitHub Actions.
5. **Security**: Input validation, output escaping, rate limiting
6. **Performance**: Redis caching for frequent queries, lazy loading for Angular modules

## Django Administration Interface

### Access
- **URL**: http://localhost:8000/admin/
- **Login**: `admin` / `admin` (superuser)

### Features Implemented

#### Models Management
- **Users (Role)**: Complete user management with custom forms
  - Email-based authentication
  - Organization assignment
  - Staff/superuser permissions
  - User-Site relationships inline

- **Organizations (BibOrganismes)**: 
  - CRUD operations for managing organizations
  - Hierarchical structure support (parent organizations)
  - Contact information management

- **Sites**:
  - Geospatial support with interactive maps (PostGIS)
  - Site classification (RNN, RNR, PNR, ENS, etc.)
  - Surface area and geographic coordinates
  - Organization-Site relationships inline
  - **Contrainte unicité INPN** : Le champ `id_inpn` est unique en base de données
  - **Détection de doublons** lors de la création :
    - Si le code INPN saisi existe déjà → **alerte bloquante** avec message "Ce code INPN est déjà utilisé par un site existant"
    - Si le nom est similaire à un site existant → **suggestions non bloquantes** de sites similaires
    - L'utilisateur peut demander l'accès au site existant ou lier son organisme

- **Nomenclatures**: 
  - Reference data management
  - Hierarchical nomenclatures support
  - Type-based classification

#### Advanced Features
- **Autocomplete fields** for Foreign Keys
- **Inline editing** for relationships
- **Geographic interface** with maps for site geometry
- **Search and filtering** optimized for each model
- **Custom forms** for user creation/modification

### Test Data Available (via `python manage.py seed_testdata`)

Run `docker compose exec web python manage.py seed_testdata` to create:

- **5 Organizations**: RNF, CEN AURA, DREAL Nouvelle-Aquitaine, Parc Ecrins, OFB
- **7 Sites**: Camargue, Aiguilles Rouges, Grand-Voyeux, Vercors, Marais de Brouage, Scandola, Lac de Remoray
- **8 Users** with different roles:
  | Email | Role | Organization | Sites | Notes |
  |-------|------|--------------|-------|-------|
  | admin@test.fr | Super Admin | RNF | Referent: Camargue | |
  | admin.rnf@test.fr | Admin Organisme | RNF | Referent: Camargue, Aiguilles Rouges | |
  | admin.cen@test.fr | Admin Organisme | CEN AURA | Referent: Grand-Voyeux, Vercors | |
  | referent.camargue@test.fr | Utilisateur | RNF | Referent: Camargue | |
  | referent.vercors@test.fr | Utilisateur | CEN AURA | Referent: Vercors | |
  | user.rnf@test.fr | Utilisateur | RNF | Membre: Camargue, Aiguilles Rouges | Voit automatiquement les plans liés |
  | user.cen@test.fr | Utilisateur | CEN AURA | Membre: Grand-Voyeux, Vercors | Voit automatiquement les plans liés |
  | **test@example.com** | Utilisateur | RNF | Referent: Camargue | **Email pour tests SMTP** |

  **Password for all test users**: `Test123!`
- **9 Plans de Gestion**: Various statuses (valide, draft, archive) with site associations and referents
  - Chaînes de versions : plan archivé → plan actif (via `plan_parent`)
  - 1 plan d'évaluation mi-parcours (brouillon, version 1.2, lié au plan Aiguilles Rouges)
- **Django Groups**: Super Administrateurs, Administrateurs Organisme, Utilisateurs
- **Nomenclatures**: Site types, evaluation types, editor types, document plan types (PLAN_INITIAL, EVAL_MI_PARCOURS, PLAN_REVISE)
- **Validation Requests (27)**: Demandes de test avec différents statuts
  - 5 demandes `plan_access` en attente (pour tester la section "Plans en attente")
  - Demandes `site_access`, `referent_validation`, `module_access`, etc.

### Authentication System (JWT)

JWT authentication is fully implemented and operational:

**Endpoints:**
- `POST /api/auth/login/` - Login with email/password → JWT tokens
- `POST /api/auth/refresh/` - Refresh access token
- `POST /api/auth/logout/` - Logout (blacklist refresh token)
- `GET /api/auth/me/` - Get current user info
- `GET /api/auth/health/` - Public health check
- `POST /api/auth/register/` - Public user registration (requires admin approval)
- `GET /api/auth/registration-status/` - Check registration request status

**Test credentials:** Voir section "Test Data Available" pour la liste complète des utilisateurs de test.

**Example usage:**
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin", "password": "admin"}'

# Use token
curl -X GET http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer {access_token}"
```

## Django Development Guide

### Understanding Migrations

Django migrations track database schema changes automatically. Voir les commandes dans la section "Development" ci-dessus.

**Migration Structure:**
- Each app has its own `migrations/` folder
- `apps/users/migrations/` → User, Site, Organization models
- `apps/core/migrations/` → Nomenclature models
- Dependencies between apps are managed automatically

**Example Workflow:**
1. Add field to `Site` model in `apps/users/models.py`
2. Run `makemigrations` → creates `0003_site_new_field.py`
3. Run `migrate` → adds column to database
4. Update `admin.py` to show new field (optional)

### Django Admin System

The admin interface is automatically generated from your models with minimal setup:

**Basic Registration:**
```python
# In admin.py - Basic interface
from django.contrib import admin
from .models import Site

admin.site.register(Site)  # Instant CRUD interface!
```

**Advanced Customization:**
```python
# Custom admin with enhanced features
@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('nom_site', 'surf_off', 'active')  # Columns
    list_filter = ('active', 'marin')                  # Filters
    search_fields = ('nom_site', 'id_local')          # Search
```

### Key Files Structure

**`admin.py`** - Admin interface customization
- Form layouts and validation
- List display configuration
- Search and filtering options
- Inline editing for relationships

**`apps.py`** - App configuration
```python
class UsersConfig(AppConfig):
    name = 'apps.users'           # Python import path
    verbose_name = 'Utilisateurs' # Admin display name
    # Can include initialization logic in ready() method
```

**`models.py`** - Database structure
- Model definitions become database tables
- Field changes trigger migration generation
- Relationships define foreign keys

**`migrations/`** - Database version control
- Auto-generated when models change
- Applied in sequence to update database
- Should never be edited manually

### Development Best Practices

**Model Changes:**
1. Always backup database before major migrations
2. Test migrations on development data first
3. Use `--fake` only when you know what you're doing

**Admin Customization:**
1. Start with basic `admin.site.register(Model)`
2. Add custom `ModelAdmin` class when needed
3. Use `readonly_fields` for calculated fields
4. Leverage `autocomplete_fields` for better UX

**Apps Organization:**
- Keep related models in the same app
- Use `core` app for shared models (like nomenclatures)
- Each app should have a clear, single responsibility

**Permissions Testing:**
- Always run `docker compose exec web python test_permissions.py` after changes
- Test API endpoints with `docker compose exec web python test_permissions_api.py`
- Use `/api/users/permissions/` to debug user permissions
- Validate middleware headers in browser developer tools

**Security Best Practices:**
- All middleware are order-dependent in `settings/base.py`
- Custom permissions inherit from `BasePermission` 
- Decorators provide function-based permission checks
- Object-level permissions via model methods (`can_manage_organisme()`)

**API REST Users:**
- Complete REST API for user management at `/api/users/`
- Full CRUD with pagination, filtering, and search
- Role-based permissions and automatic data filtering
- Comprehensive documentation in `docs/API_USERS_GUIDE.md`

**API REST Organismes and Sites:**
- Complete REST API for organizations and sites management
- GeoJSON support for PostGIS geometries (import/export)
- Nested routes `/organismes/{id}/sites/` and bulk operations
- Advanced geospatial filtering and search capabilities
- Comprehensive documentation in `docs/API_ORGANISMES_SITES_GUIDE.md`

**API REST Plans de Gestion:**
- Complete REST API for management plans at `/api/plans/plans/`
- Full CRUD with multi-site support and file attachments
- 20+ endpoints including GeoJSON, statistics, bulk operations
- Advanced filtering (25+ filters) and search capabilities
- Upload/download system for plan files (documents, maps, reports)
- **Cycle de vie des plans** :
  - `POST /api/plans/plans/{id}/change-status/` - Changement de statut (référent du plan, admin_og+)
    - Transitions : `draft↔valide`, `valide→archive`, `archive→draft`
  - `POST /api/plans/plans/{id}/create-evaluation/` - Création d'une évaluation mi-parcours (référent du plan, admin_og+). Plan source doit être `valide` et de type plan (pas évaluation). Copie sites/référents, version incrémentée.
  - `POST /api/plans/plans/{id}/duplicate/` - Duplication d'un plan avec options sélectives
  - Chaîne de versions via `plan_parent` FK et `id_type_document` (nomenclature)
  - Le serializer détail expose `version_chain` pour la timeline frontend
  - **Statuts** : `draft` (brouillon), `valide` (actif), `archive` (inactif)
  - **Permissions lifecycle** : référent du plan (`PlanGestion.referents`), admin_og, super_admin. Vérification spécifique au plan dans la vue (pas juste le rôle global).
- Comprehensive documentation in `docs/API_PLANS_GUIDE.md`

**API REST Notifications & Validations:**
- Validation requests API at `/api/validations/`
- Request types: `user_registration`, `site_access`, `plan_access`, `referent_validation`, `plan_site_link`
- Status workflow: `pending` → `approved` / `rejected` / `cancelled` / `expired`
- Endpoints:
  - `GET /api/validations/` - List validation requests (filtered by user role)
  - `GET /api/validations/pending/` - Pending requests for current validator
  - `GET /api/validations/my-requests/` - Current user's own requests
  - `POST /api/validations/{id}/approve/` - Approve a request
  - `POST /api/validations/{id}/reject/` - Reject a request
  - `POST /api/validations/request_plan_site_link/` - Demande de lien plan-site (body: `{plan_id, site_id}`)
  - `GET /api/notifications/` - User notifications
  - `POST /api/notifications/{id}/read/` - Mark notification as read
  - `POST /api/notifications/read-all/` - Mark all as read

**Validation plan-site link** (`plan_site_link`) :
- **Droits** : référent du plan, membre du plan, référent/membre du site, admin_og+
- **Lien direct** (sans validation) : super_admin, admin_og+référent site, référent plan+référent site
- **Validation requise** : dans tous les autres cas
  - Si le demandeur est **référent du plan** → validateurs = référents du site + admin_og du site
  - Sinon (membre du plan, référent/membre du site) → validateurs = référents du plan
- **Approbation** : crée `CorSitePg` + notifie le demandeur + notifie les référents du plan

**Types de notifications disponibles:**
| Type | Description | Déclencheur |
|------|-------------|-------------|
| `welcome` | Bienvenue | Activation du compte après validation |
| `validation_request` | Demande de validation | Nouvelle demande reçue (pour validateurs) |
| `validation_approved` | Validation approuvée | Demande approuvée |
| `validation_rejected` | Validation rejetée | Demande rejetée |
| `user_associated_site` | Associé à un site | Ajout comme membre d'un site |
| `user_associated_plan` | Associé à un plan | Ajout comme référent d'un plan |
| `user_removed_site` | Retiré d'un site | Retrait d'un site |
| `user_removed_plan` | Retiré d'un plan | Retrait d'un plan |
| `account_deactivated` | Compte désactivé | Désactivation par un admin |
| `account_activated` | Compte activé | Réactivation par un admin |
| `organisme_changed` | Organisme modifié | Changement d'organisme par un admin |
| `site_orphaned` | Site sans utilisateurs | Plus aucun utilisateur sur le site |
| `organisme_no_admin` | Organisme sans admin | Plus d'administrateur pour l'organisme |
| `system_alert` | Alerte système | Notifications système (maintenance, etc.) |
| `info` | Information | Informations générales |

**Signaux de notifications automatiques** (`apps/notifications/signals.py`):
- `notify_user_site_association`: Notifie lors de l'ajout à un site
- `notify_user_removed_from_site`: Notifie lors du retrait d'un site
- `notify_user_deactivation`: Notifie lors de la désactivation
- `notify_user_organisme_changed`: Notifie lors du changement d'organisme
- `notify_plan_referents_new_member`: Notifie les référents d'un plan lors de l'ajout d'un membre/référent

**Notifications liées aux validations plan-site** :
- Lors de l'approbation d'un lien plan-site (`approve_plan_site_link`), les référents du plan sont notifiés que le site a été lié
- Lors d'un lien direct plan-site (sans validation), les référents du plan sont également notifiés

**API REST Activity (Historique d'activité):**
- Unified activity timeline API at `/api/activity/`
- Entity types: `site`, `plan`, `user`, `organisme`, `validation`
- Action types: `create`, `update`, `delete`, `add_member`, `remove_member`, `add_referent`, `remove_referent`, `status_change`, `activate`, `deactivate`, `rgpd_request`, `rgpd_cancelled`, `rgpd_anonymized`, etc.
- Visibility levels: `public`, `admin`, `system`
- Filtering by user role:
  | Rôle | Accès |
  |------|-------|
  | super_admin | Tout (y compris RGPD et système) |
  | admin_og | Activité de son organisme |
  | référent | Activité de ses sites/plans |
  | utilisateur | Ses notifications + sites où il est membre |

- Endpoints:
  - `GET /api/activity/` - List activities (paginated, filtered by role)
  - `GET /api/activity/{id}/` - Single activity detail
  - `GET /api/activity/my_sites/` - Activities for user's sites
  - `GET /api/activity/my_plans/` - Activities for user's plans
  - `GET /api/activity/validations/` - Validation-related activities (admin_og+)
  - `GET /api/activity/rgpd/` - RGPD activities (super_admin only)
  - `GET /api/activity/system/` - System activities (super_admin only)
  - `GET /api/activity/stats/` - Activity statistics
  - `GET /api/activity/tabs_counts/` - Counts per tab/category

- Filters:
  - `entity_type` - Filter by entity type (site, plan, user, etc.)
  - `action` - Filter by action type
  - `site_id` - Filter by related site
  - `plan_id` - Filter by related plan
  - `since` - Filter by date (ISO format)
  - `search` - Text search in description/entity_name

- Backend components:
  - Model: `apps/core/models.py` → `ActivityLog`
  - Service: `apps/core/services.py` → `ActivityService`
  - Signals: `apps/core/activity_signals.py` (auto-logging on model changes)
  - API: `apps/core/views.py` → `ActivityViewSet`

- Tests: `tests/apps/core/test_activity.py` (45 tests)

### Frontend Features

**Page Profil (`/profile`):**
- Informations personnelles de l'utilisateur
- Onglet "Mes demandes" : suivi des demandes de validation en cours
- Accessible à tous les utilisateurs authentifiés

**Administration Validations (`/admin/validations`):**
- Tableau des demandes de validation à traiter
- Filtres par statut et type de demande
- Actions rapides : approuver/rejeter en un clic
- Dialog de détail avec informations complètes
- Accessible aux admin_og et super_admin

**Inscription Publique (`/auth/register`):**
- Formulaire d'inscription avec sélection d'organisme
- Page d'attente de validation (`/auth/registration-pending`)
- Workflow : inscription → validation admin → activation compte

**Cloche de Notifications:**
- Composant `NotificationBellComponent` dans le header
- Compteur de notifications non lues
- Dialog avec liste des notifications et marquage comme lu
- Lien "Voir tout" vers `/activite`

**Page Activité (`/activite`):**
- Timeline unifiée des activités, notifications et validations
- Onglets dynamiques selon le rôle de l'utilisateur:
  - **Tous les utilisateurs**: "Tout", "Mes sites", "Mes plans", "Mes droits", "Notifications"
  - **Admin organisme+**: + "Validations"
  - **Super admin**: + "RGPD", "Système"
- **Onglet "Mes droits"**: Historique des changements de droits de l'utilisateur (ajout/retrait membre, référent, activation compte, validation demandes)
- Filtres par type d'entité, action, recherche textuelle
- Groupement chronologique ("Aujourd'hui", "Hier", "Cette semaine", etc.)
- Icônes et couleurs par type d'action (création=vert, modification=bleu, suppression=rouge)
- Pagination avec scroll infini
- Liens vers les entités concernées

Fichiers frontend:
- Route: `frontend/src/app/features/activity/activity.routes.ts`
- Composant principal: `frontend/src/app/features/activity/activity.component.ts`
- Service: `frontend/src/app/core/services/activity.service.ts`
- Modèles: `frontend/src/app/core/models/activity.model.ts`
- Traductions: `frontend/src/assets/i18n/fr.json` (clés `activity.*`)

**Cycle de vie des Plans (`/plans/:slug`):**
- **Statuts** : `draft` (brouillon), `valide` (actif), `archive` (inactif)
- **Droits** : Actions de cycle de vie accessibles uniquement aux **référents du plan**, **admin organisme** et **super admin**. Calculé via `canManageLifecycle` computed dans `plan-detail.component.ts` (vérifie `plan.referents`, `authService.isAdminOrganisme()`, `authService.isSuperAdmin()`).
- **PlanVersionTimelineComponent** : Timeline verticale des versions dans la colonne latérale (section "Cycle de vie")
  - Nœuds cliquables (cercles avec icône type document), connectés par une ligne verticale
  - Nœud courant mis en avant : fond coloré, bordure gauche terra-cotta, badge "actuel"
  - Masqué si `version_chain.length <= 1`
  - **Actions contextuelles** intégrées sous la timeline (si `canManage`) :
    - Brouillon → "Valider le plan"
    - Validé → "Remettre en brouillon" + "Lancer évaluation mi-parcours" (seulement plans, pas évaluations) + "Archiver (rend inactif)"
    - Archivé → "Réactiver (rend actif)"
  - Fichiers : `shared/components/plan-version-timeline/`
- **StatusChangeDialogComponent** : Modale de changement de statut (alternative aux actions timeline, utilisée depuis la liste)
  - Fichiers : `shared/components/modals/status-change-dialog/`
- **DuplicatePlanDialogComponent** : Modale de duplication de plan avec options sélectives
  - Fichiers : `shared/components/modals/duplicate-plan-dialog/`
- Traductions : `frontend/src/assets/i18n/fr.json` (clés `plans.lifecycle.*`, `plans.duplicate.*`)

## Internationalisation (i18n)

**IMPORTANT : Toutes les chaînes de texte visibles par l'utilisateur doivent être traduites.**

### Frontend (Angular avec ngx-translate)

**Configuration :**
- Fichier de traductions : `frontend/src/assets/i18n/fr.json`
- Service : `frontend/src/app/core/services/translation.service.ts`
- Langue par défaut : Français (`fr`)

**Usage dans les templates HTML :**
```html
<!-- Texte simple -->
<h1>{{ 'admin.users.title' | translate }}</h1>

<!-- Avec paramètres -->
<p>{{ 'common.itemsCount' | translate:{ count: items.length } }}</p>

<!-- Dans les attributs -->
<input [placeholder]="'common.actions.search' | translate">
<button [title]="'common.actions.delete' | translate">
```

**Usage dans le TypeScript :**
```typescript
import { TranslateService } from '@ngx-translate/core';

// Dans le composant
private readonly translate = inject(TranslateService);

// Utilisation
this.snackBar.open(
  this.translate.instant('admin.users.messages.success'),
  this.translate.instant('common.actions.close'),
  { duration: 3000 }
);
```

**Structure des clés de traduction :**
```
common.actions.*      - Actions (save, cancel, delete, close, search...)
common.status.*       - Statuts (active, inactive, pending...)
common.validation.*   - Messages de validation
auth.*                - Authentification (login, register)
header.*              - Navigation et header
admin.users.*         - Gestion des utilisateurs
admin.plans.*         - Gestion des plans
admin.sites.*         - Gestion des sites
admin.organismes.*    - Gestion des organismes
admin.validations.*   - Gestion des validations
modals.*              - Dialogues modaux
plans.*               - Module plans
profile.*             - Page profil
home.*                - Page d'accueil
scores.*              - Labels des scores
actionStatus.*        - Statuts des actions
```

**Ajouter TranslateModule aux composants standalone :**
```typescript
import { TranslateModule } from '@ngx-translate/core';

@Component({
  // ...
  imports: [CommonModule, TranslateModule, /* autres imports */],
})
```

### Backend (Django avec gettext)

**Configuration :**
- Répertoire locale : `backend/locale/fr/LC_MESSAGES/`
- Import : `from django.utils.translation import gettext_lazy as _`

**Fichiers de traduction Django :**

| Fichier | Type | Description |
|---------|------|-------------|
| `.po` (Portable Object) | Texte | Fichier éditable contenant les chaînes source et leurs traductions |
| `.mo` (Machine Object) | Binaire | Fichier compilé utilisé par Django à l'exécution |

**Workflow de traduction :**
1. `makemessages` → Scanne le code Python/templates et génère/met à jour les `.po`
2. Édition manuelle → Traduire les chaînes dans le fichier `.po`
3. `compilemessages` → Compile les `.po` en `.mo` pour la production

**Note importante :** Avec `gettext_lazy`, les chaînes françaises sont directement dans le code Python. Les fichiers `.po`/`.mo` ne sont nécessaires que si vous ajoutez une **autre langue** (ex: anglais). Pour le français uniquement, l'infrastructure actuelle suffit.

**Usage dans les models :**
```python
from django.utils.translation import gettext_lazy as _

class MonModel(models.Model):
    nom = models.CharField(_("Nom"), max_length=100)
    description = models.TextField(_("Description"), help_text=_("Description détaillée"))

    class Meta:
        verbose_name = _("Mon modèle")
        verbose_name_plural = _("Mes modèles")
```

**Usage dans les serializers/views :**
```python
from django.utils.translation import gettext_lazy as _

raise serializers.ValidationError(_("Les mots de passe ne correspondent pas."))
```

**Usage dans les templates email :**
```html
{% load i18n %}

<h1>{% trans "Bienvenue" %}</h1>
<p>{% blocktrans %}Bonjour {{ nom }},{% endblocktrans %}</p>
```

**Commandes de traduction (uniquement si ajout d'une nouvelle langue) :**
```bash
# Installer gettext dans le container (requis une seule fois)
docker compose exec web apk add gettext

# Extraire les chaînes traduisibles vers backend/locale/fr/LC_MESSAGES/django.po
docker compose exec web python manage.py makemessages -l fr

# Pour ajouter l'anglais
docker compose exec web python manage.py makemessages -l en

# Compiler les .po en .mo (après traduction manuelle du .po)
docker compose exec web python manage.py compilemessages
```

**Contenu d'un fichier .po :**
```po
#: apps/users/models.py:42
msgid "Adresse email"
msgstr "Adresse email"  # FR: identique car source en français

#: apps/users/models.py:42 (dans en/django.po)
msgid "Adresse email"
msgstr "Email address"  # EN: traduction anglaise
```

### Bonnes pratiques

1. **Ne jamais coder en dur** les textes visibles par l'utilisateur
2. **Utiliser des clés descriptives** : `admin.users.messages.deleteSuccess` plutôt que `msg1`
3. **Grouper les clés** par fonctionnalité/module
4. **Ajouter les traductions** dans `fr.json` AVANT de les utiliser
5. **Vérifier** que TranslateModule est importé dans les composants standalone

For detailed specifications, model definitions, and full documentation, refer to `claude.md`.