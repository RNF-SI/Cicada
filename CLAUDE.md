# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Outil Plan de Gestion** - Web application for managing conservation area management plans, developed for CEN (Conservatoire d'Espaces Naturels) and RNF (Réserves Naturelles de France).

- **Current Status**: Greenfield project - specifications defined, implementation not started
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

### Initial Project Setup (To Be Implemented)

```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser

# Frontend setup
cd frontend
npm install
npm run build

# Docker setup
docker-compose up -d
```

### Development

```bash
# Backend
cd backend && python manage.py runserver

# Frontend  
cd frontend && ng serve

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create new Django app
python manage.py startapp <app_name>
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

For detailed specifications, model definitions, and full documentation, refer to `claude.md`.