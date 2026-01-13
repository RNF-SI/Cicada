# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Outil Plan de Gestion** - Web application for managing conservation area management plans, developed for CEN (Conservatoire d'Espaces Naturels) and RNF (Réserves Naturelles de France).

- **Current Status**: Plans de Gestion models implemented, Django admin configured
- **Architecture Documentation**: See `claude.md` for detailed specifications
- **Repository**: https://github.com/RNF-SI/outil_plan_de_gestion

## Technology Stack

### Backend
- Django 5.0+ with Django REST Framework 3.14+
- PostgreSQL 15+ with PostGIS 3.3+ for spatial data
- Python 3.11+
- Celery + Redis for async tasks (email notifications)

### Frontend
- Angular 19+ with TypeScript 5+
- Angular Material for UI components
- Leaflet for interactive maps
- **Design System**: Custom SCSS based on Kit UI Biodiv' France (11/2025)
  - **Source de référence**: `KitUI/` (PNG des maquettes)
  - **Status**: ⚠️ 95% complet
  - **Fichiers SCSS**: 5 fichiers (~3000 lignes)
    - `_variables.scss` - Tokens (couleurs, spacing, typography)
    - `_typography.scss` - Styles typographiques
    - `_material-overrides.scss` - Personnalisation Angular Material
    - `_components.scss` - Composants custom (jauges, tuiles, breadcrumb, etc.)
    - `_filters.scss` - Filtres et pagination
  - **Couleurs**: Conformes Kit UI 11/2025
    - Primary: #025359 (Bleu-vert)
    - Secondary: #FEC180 (Jaune), #F5B399 (Orange saumon), #B74D5D (Terra Cotta), #C0E3CF (Vert pâle)
    - Scores: #FF7579, #FA9965, #F7D35C, #82DB8A, #81C9D8
    - Status: #04854B (Succès), #E12329 (Erreur), #FA9965 (Warning), #81C9D8 (Info)
  - **Font**: Nunito (Google Font)
  - **Accessibilité**: WCAG AA compliant
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
docker-compose up -d

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
docker-compose exec web python manage.py runserver

# Database migrations
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python create_superuser.py

# Create test data (Django management command)
docker-compose exec web python manage.py seed_testdata          # Create all test data
docker-compose exec web python manage.py seed_testdata --reset  # Remove test data
docker-compose exec web python manage.py seed_testdata --dry-run # Preview changes

# Import/Update nomenclatures (reference data)
docker-compose exec web python import_nomenclatures.py

# Test nomenclatures import
docker-compose exec web python test_nomenclatures.py

# Access Django shell
docker-compose exec web python manage.py shell
```

### Logging

```bash
# Logs en temps réel (filtrés sur les requêtes et erreurs)
docker-compose logs -f web | grep -E "(Request|AUDIT|ERROR)"

# Tous les logs en temps réel
docker-compose logs -f web
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

### Testing

> **Documentation complète** : Voir [`docs/TESTING.md`](docs/TESTING.md) pour le guide détaillé des tests.

#### Résumé de la couverture

| Stack | Framework | Tests | Couverture |
|-------|-----------|-------|------------|
| Backend | pytest + pytest-django + Factory Boy | 356 | 56% |
| Frontend | Jest + jest-preset-angular | 132 | 7% |
| **Total** | | **488** | |

#### Backend (pytest)

```bash
# Via Docker (recommandé)
docker-compose exec web pytest tests/

# Avec couverture HTML
docker-compose exec web pytest tests/ --cov=apps --cov-report=html

# Tests unitaires uniquement
docker-compose exec web pytest tests/ -m unit

# Tests d'intégration uniquement
docker-compose exec web pytest tests/ -m integration

# Un fichier spécifique
docker-compose exec web pytest tests/integration/test_api_users.py -v

# Un test spécifique
docker-compose exec web pytest tests/integration/test_api_users.py::TestUsersListEndpoint -v
```

**Structure des tests backend :**
```
backend/tests/
├── factories/           # Factory Boy (UserFactory, PlanGestionFactory, etc.)
├── apps/               # Tests unitaires
│   ├── users/          # test_models.py, test_permissions.py, test_middleware.py
│   └── plans/          # test_views.py, test_filters.py
└── integration/        # Tests API
    ├── test_api_auth.py
    ├── test_api_users.py
    ├── test_api_org_sites.py
    └── test_api_plans.py
```

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

#### CI/CD

Les tests s'exécutent automatiquement via GitHub Actions sur chaque push/PR vers `main` ou `develop`.
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
- **Design System**: Custom SCSS implementing Kit UI Biodiv' France (11/2025)
  - Variables: `src/assets/scss/_variables.scss`
  - Typography: `src/assets/scss/_typography.scss`
  - Material overrides: `src/assets/scss/_material-overrides.scss`
  - Custom components: `src/assets/scss/_components.scss`
  - Filters & pagination: `src/assets/scss/_filters.scss`
  - Main styles: `src/styles.scss`
  - Reference: `KitUI/` (PNG maquettes)

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

The application uses PostgreSQL with PostGIS and follows a multi-schema approach:

1. **utilisateurs schema**: User management
   - `t_roles`: User accounts with email as unique identifier
   - `bib_organismes`: Management organizations
   - `cor_role_ep`: User-Site relationships with permissions

2. **referentiels schema**: Reference data
   - `t_espace_protege`: Protected areas with PostGIS geometries
   - `t_nomenclatures`: Reference lists and categories

3. **general schema**: Application data
   - `t_plan_gestion`: Management plans
   - `cor_site_pg`: Many-to-many between plans and sites (renamed for terminology consistency)
   - `cor_pg_fichier`: File attachments for management plans

### Frontend Architecture

Angular application with:
- **core module**: Singleton services (auth, API client, interceptors)
- **shared module**: Reusable components, pipes, directives
- **feature modules**: Plans, users, auth (lazy loaded)
- **State management**: RxJS-based with services as stores

## Key Implementation Patterns

### Authentication & Permissions

- **User Roles**: Super Admin > Admin Organisme > Utilisateur
- **Référent** (access level, not a role): User is "referent" if assigned as site referent (`CorRoleSite.referent=True`) or plan referent (`PlanGestion.referents`)
- **Permission Model**: Role-based with hierarchical access and Django groups
- **JWT Implementation**: djangorestframework-simplejwt with 60min access + 7-day refresh tokens
- **Security Middleware**: 3 custom middleware for headers, permissions, and audit
- **API Protection**: All endpoints protected by default except `/api/auth/`
- **Permissions Classes**: Custom DRF permissions + decorators for granular control

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
4. **Testing**:
   - Backend : 317 tests (62% couverture) - pytest + Factory Boy
   - Frontend : 55 tests (100% auth) - Jest
   - CI/CD : GitHub Actions sur push/PR
   - Objectif : 80% backend, 70% frontend
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

Run `docker-compose exec web python manage.py seed_testdata` to create:

- **5 Organizations**: RNF, CEN AURA, DREAL Nouvelle-Aquitaine, Parc Ecrins, OFB
- **7 Sites**: Camargue, Aiguilles Rouges, Grand-Voyeux, Vercors, Marais de Brouage, Scandola, Lac de Remoray
- **7 Users** with different roles:
  | Email | Role | Organization | Notes |
  |-------|------|--------------|-------|
  | admin@test.fr | Super Admin | - | |
  | admin.rnf@test.fr | Admin Organisme | RNF | |
  | admin.cen@test.fr | Admin Organisme | CEN AURA | |
  | referent.camargue@test.fr | Utilisateur | RNF | Site referent (Camargue) |
  | referent.vercors@test.fr | Utilisateur | CEN AURA | Site referent (Vercors) |
  | user.rnf@test.fr | Utilisateur | RNF | |
  | user.cen@test.fr | Utilisateur | CEN AURA | |

  **Password for all test users**: `Test123!`
- **6 Plans de Gestion**: Various statuses (valide, draft, archive) with site associations
- **Django Groups**: Super Administrateurs, Administrateurs Organisme, Utilisateurs
- **Nomenclatures**: Site types, evaluation types, editor types
- **Validation Requests**: Demandes de test avec différents statuts (pending, approved, rejected) et dates réalistes

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

**Configuration:**
- Access tokens: 60 minutes lifetime
- Refresh tokens: 7 days with rotation
- Email-based authentication (not username)
- All API endpoints protected by default

**Test credentials:**
- `admin` / `admin` (superuser)
- `marie.dupont@rnf.fr` / `password123` (user with organization)

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

Django migrations track database schema changes automatically:

```bash
# 1. Modify models.py (add/remove/change fields)
# 2. Generate migration file
docker-compose exec web python manage.py makemigrations

# 3. Apply changes to database
docker-compose exec web python manage.py migrate
```

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

**Permissions System:**
- **3 role levels**: utilisateur → admin_og → super_admin
- **Referent access**: Computed via `is_referent()` - true if user is site or plan referent
- **10 custom permissions** + Django standard (add/change/view/delete)
- **Permission check methods**: `user.is_super_admin()`, `user.is_referent()`, `user.can_manage_site(site)`
- **DRF classes**: `IsSuperAdmin`, `IsAdminOrganisme`, `IsReferent`
- **Decorators**: `@require_super_admin`, `@require_admin_organisme`

**Permissions Testing:**
- Always run `docker-compose exec web python test_permissions.py` after changes
- Test API endpoints with `docker-compose exec web python test_permissions_api.py`
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
- Comprehensive documentation in `docs/API_PLANS_GUIDE.md`

**API REST Notifications & Validations:**
- Validation requests API at `/api/validations/`
- Request types: `user_registration`, `site_access`, `plan_access`, `referent_validation`
- Status workflow: `pending` → `approved` / `rejected` / `cancelled` / `expired`
- Endpoints:
  - `GET /api/validations/` - List validation requests (filtered by user role)
  - `GET /api/validations/pending/` - Pending requests for current validator
  - `GET /api/validations/my-requests/` - Current user's own requests
  - `POST /api/validations/{id}/approve/` - Approve a request
  - `POST /api/validations/{id}/reject/` - Reject a request
  - `GET /api/notifications/` - User notifications
  - `POST /api/notifications/{id}/read/` - Mark notification as read
  - `POST /api/notifications/read-all/` - Mark all as read

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
docker-compose exec web apk add gettext

# Extraire les chaînes traduisibles vers backend/locale/fr/LC_MESSAGES/django.po
docker-compose exec web python manage.py makemessages -l fr

# Pour ajouter l'anglais
docker-compose exec web python manage.py makemessages -l en

# Compiler les .po en .mo (après traduction manuelle du .po)
docker-compose exec web python manage.py compilemessages
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