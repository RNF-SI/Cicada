# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Outil Plan de Gestion** - Web application for managing conservation area management plans, developed for CEN (Conservatoire d'Espaces Naturels) and RNF (Réserves Naturelles de France).

- **Current Status**: Models implemented, Django admin configured
- **Architecture Documentation**: See `claude.md` for detailed specifications
- **Repository**: https://github.com/RNF-SI/outil_plan_de_gestion

## Technology Stack

### Backend
- Django 5.0+ with Django REST Framework 3.14+
- PostgreSQL 15+ with PostGIS 3.3+ for spatial data
- Python 3.11+

### Frontend  
- Angular 19+ with TypeScript 5+
- Angular Material for UI components
- Leaflet for interactive maps

## Common Development Commands

### Project Setup (Current Implementation)

```bash
# Docker setup (recommended)
docker-compose up -d

# The setup includes:
# - PostgreSQL with PostGIS
# - Redis for caching
# - Django backend with migrations applied
# - Static files collection
# - Test data creation
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

# Create test data
docker-compose exec web python create_test_data.py

# Access Django shell
docker-compose exec web python manage.py shell
```

### Testing

```bash
# Backend tests
cd backend && pytest
pytest --cov=apps --cov-report=html  # With coverage
pytest -k test_name  # Run specific test

# Frontend tests
cd frontend && npm test
npm run test:coverage
npm run e2e  # Cypress tests
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

### Django Apps Structure

The backend follows a modular architecture with distinct Django apps:

- **authentication**: JWT auth, permissions, user onboarding workflow
- **users**: User management, organizations (bib_organismes), role-based access
- **plans**: Management plans CRUD, multi-site support, file attachments
- **api**: Public API endpoints with token auth
- **core**: Shared utilities, base models, common middleware

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
   - `cor_ep_pg`: Many-to-many between plans and sites

### Frontend Architecture

Angular application with:
- **core module**: Singleton services (auth, API client, interceptors)
- **shared module**: Reusable components, pipes, directives
- **feature modules**: Plans, users, auth (lazy loaded)
- **State management**: RxJS-based with services as stores

## Key Implementation Patterns

### Authentication & Permissions

- **User Roles**: Super Admin > Organization Admin > Referent > User
- **Permission Model**: Role-based with organization-scoped access
- **Onboarding Flow**: New users require organization admin approval
- **API Auth**: JWT tokens for internal, token-based for public API

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
4. **Testing**: Minimum 80% backend, 70% frontend coverage
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

### Test Data Available
- **3 Organizations**: RNF, CEN Auvergne-Rhône-Alpes, DREAL
- **3 Sites**: Camargue, Aiguilles Rouges, Grand-Voyeux
- **5 Site Types**: RNN, RNR, PNR, ENS nomenclatures
- **3 Users**: Admin + 2 test users

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

For detailed specifications, model definitions, and full documentation, refer to `claude.md`.