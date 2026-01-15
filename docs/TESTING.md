# Guide des Tests - CICADA

Ce document décrit la stratégie de tests, les outils utilisés, et les fonctionnalités couvertes par les tests automatisés.

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Backend (Django/pytest)](#backend-djangopytest)
- [Frontend (Angular/Jest)](#frontend-angularjest)
- [Exécution des tests](#exécution-des-tests)
- [Fonctionnalités testées](#fonctionnalités-testées)
- [Prochaines étapes](#prochaines-étapes)
- [CI/CD avec GitHub Actions](#cicd-avec-github-actions)

---

## Vue d'ensemble

| Stack | Framework | Tests | Couverture |
|-------|-----------|-------|------------|
| Backend | pytest + pytest-django | 317 | 62% |
| Frontend | Jest + jest-preset-angular | 55 | 10% global, 100% auth |
| **Total** | - | **372** | - |

### Architecture des tests

```
Cicada/
├── backend/
│   ├── pytest.ini                 # Configuration pytest
│   ├── conftest.py                # Fixtures globales
│   └── tests/
│       ├── factories/             # Factory Boy factories
│       │   ├── users.py
│       │   ├── plans.py
│       │   └── core.py
│       ├── apps/                  # Tests unitaires
│       │   ├── users/
│       │   │   ├── test_models.py
│       │   │   ├── test_permissions.py
│       │   │   └── test_middleware.py
│       │   └── plans/
│       │       ├── test_views.py
│       │       └── test_filters.py
│       └── integration/           # Tests d'intégration API
│           ├── test_api_auth.py
│           ├── test_api_users.py
│           ├── test_api_org_sites.py
│           └── test_api_plans.py
│
└── frontend/
    ├── jest.config.js             # Configuration Jest
    ├── setup-jest.ts              # Setup environnement
    ├── tsconfig.spec.json         # TypeScript pour tests
    └── src/app/core/
        ├── services/
        │   └── auth.service.spec.ts
        ├── guards/
        │   └── auth.guard.spec.ts
        └── interceptors/
            └── auth.interceptor.spec.ts
```

---

## Backend (Django/pytest)

### Outils utilisés

| Outil | Version | Usage |
|-------|---------|-------|
| pytest | 7.4+ | Framework de test |
| pytest-django | 4.8+ | Intégration Django |
| pytest-cov | 4.1+ | Rapports de couverture |
| factory-boy | 3.3+ | Génération de données de test |
| Faker | 38+ | Données aléatoires réalistes |

### Types de tests

#### 1. Tests Unitaires (`tests/apps/`)

Tests isolés des composants individuels sans dépendances externes.

**Modèles (`test_models.py`)**
```python
@pytest.mark.unit
class TestRoleModel:
    def test_create_user(self, db):
        user = Role.objects.create_user(email='test@example.com', password='test')
        assert user.email == 'test@example.com'
```

**Permissions (`test_permissions.py`)**
```python
@pytest.mark.unit
class TestIsSuperAdminPermission:
    def test_super_admin_has_permission(self):
        permission = IsSuperAdmin()
        assert permission.has_permission(request, view) is True
```

**Middleware (`test_middleware.py`)**
```python
@pytest.mark.unit
class TestPermissionMiddleware:
    def test_adds_permission_headers(self):
        response = middleware(request)
        assert 'X-User-Role' in response.headers
```

#### 2. Tests d'Intégration (`tests/integration/`)

Tests des endpoints API complets avec base de données.

```python
@pytest.mark.django_db
@pytest.mark.integration
class TestUsersListEndpoint:
    def test_list_super_admin_sees_all(self, api_client):
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/users/')
        assert response.status_code == 200
```

### Factories disponibles

| Factory | Fichier | Description |
|---------|---------|-------------|
| `UserFactory` | users.py | Utilisateur standard |
| `SuperAdminFactory` | users.py | Super administrateur |
| `AdminOrganismeFactory` | users.py | Admin d'organisme |
| `ReferentFactory` | users.py | Référent de site |
| `OrganismeFactory` | users.py | Organisation |
| `SiteFactory` | users.py | Site protégé (avec géométrie) |
| `PlanGestionFactory` | plans.py | Plan de gestion |
| `CorSitePgFactory` | plans.py | Association site-plan |
| `CorPgFichierFactory` | plans.py | Fichier attaché |
| `NomenclatureTypeFactory` | core.py | Type de nomenclature |
| `NomenclatureFactory` | core.py | Nomenclature |

### Fixtures globales (conftest.py)

```python
# Clients API
api_client          # Client non authentifié
authenticated_client # (client, user) - utilisateur standard
super_admin_client   # (client, admin) - super admin
admin_og_client      # (client, admin_og) - admin organisme
referent_client      # (client, referent) - référent

# Factories (accessibles dans les tests)
user_factory
super_admin_factory
organisme_factory
site_factory
plan_factory
nomenclature_factory
```

### Markers pytest

```python
@pytest.mark.unit        # Test unitaire
@pytest.mark.integration # Test d'intégration
@pytest.mark.slow        # Test lent (> 1s)
```

---

## Frontend (Angular/Jest)

### Outils utilisés

| Outil | Version | Usage |
|-------|---------|-------|
| Jest | 29.7+ | Framework de test |
| jest-preset-angular | 14+ | Preset Angular |
| @types/jest | 29.5+ | Types TypeScript |

### Types de tests

#### 1. Tests de Services

```typescript
describe('AuthService', () => {
  it('should login successfully', fakeAsync(() => {
    service.login({ username: 'test@example.com', password: 'password' }).subscribe();
    const req = httpMock.expectOne('/api/auth/login/');
    req.flush(mockLoginResponse);
    expect(service.isAuthenticated()).toBe(true);
  }));
});
```

#### 2. Tests de Guards

```typescript
describe('authGuard', () => {
  it('should allow access when authenticated', () => {
    mockAuthService.isAuthenticated.mockReturnValue(true);
    const result = TestBed.runInInjectionContext(() => authGuard(mockRoute, mockState));
    expect(result).toBe(true);
  });
});
```

#### 3. Tests d'Interceptors

```typescript
describe('AuthInterceptor', () => {
  it('should add Authorization header', () => {
    mockAuthService.getAccessToken.mockReturnValue('token');
    httpClient.get('/api/users/').subscribe();
    const req = httpMock.expectOne('/api/users/');
    expect(req.request.headers.get('Authorization')).toBe('Bearer token');
  });
});
```

### Configuration Jest

```javascript
// jest.config.js
module.exports = {
  preset: 'jest-preset-angular',
  setupFilesAfterEnv: ['<rootDir>/setup-jest.ts'],
  collectCoverageFrom: [
    'src/app/**/*.ts',
    '!src/app/**/*.module.ts',
    '!src/app/**/*.routes.ts'
  ],
  moduleNameMapper: {
    '@app/(.*)': '<rootDir>/src/app/$1',
    '@core/(.*)': '<rootDir>/src/app/core/$1'
  }
};
```

---

## Exécution des tests

### Backend

```bash
# Via Docker (recommandé)
docker-compose exec web pytest tests/

# Tous les tests avec couverture
docker-compose exec web pytest tests/ --cov=apps --cov-report=html

# Tests unitaires uniquement
docker-compose exec web pytest tests/ -m unit

# Tests d'intégration uniquement
docker-compose exec web pytest tests/ -m integration

# Un fichier spécifique
docker-compose exec web pytest tests/integration/test_api_users.py -v

# Un test spécifique
docker-compose exec web pytest tests/integration/test_api_users.py::TestUsersListEndpoint::test_list_super_admin_sees_all -v

# Mode verbose avec détails d'erreur
docker-compose exec web pytest tests/ -v --tb=long
```

### Frontend

```bash
cd frontend

# Tous les tests
npm test

# Mode watch (développement)
npm run test:watch

# Avec couverture
npm run test:coverage

# Un fichier spécifique
npm test -- src/app/core/services/auth.service.spec.ts
```

---

## Fonctionnalités testées

### Backend - Couverture par module

#### Module Users (apps/users)

| Fonctionnalité | Tests | Couverture |
|----------------|-------|------------|
| **Modèles** | | |
| Création utilisateur | ✅ | 94% |
| Méthodes de rôle (is_super_admin, etc.) | ✅ | 100% |
| Relations organisme/site | ✅ | 90% |
| **Permissions DRF** | | |
| IsSuperAdmin | ✅ | 100% |
| IsAdminOrganisme | ✅ | 100% |
| IsReferent | ✅ | 100% |
| CanManageOrganisme | ✅ | 100% |
| CanManageSite | ✅ | 100% |
| HasPlanGestionAccess | ✅ | 100% |
| **Middleware** | | |
| PermissionMiddleware | ✅ | 95% |
| SecurityHeadersMiddleware | ✅ | 100% |
| AuditMiddleware | ✅ | 90% |
| **API Users** | | |
| CRUD utilisateurs | ✅ | 88% |
| Endpoint /me | ✅ | 100% |
| Changement mot de passe | ✅ | 100% |
| Assignation sites | ✅ | 100% |
| Filtres et recherche | ✅ | 71% |
| Pagination | ✅ | 100% |
| **API Organismes** | | |
| CRUD organismes | ✅ | 78% |
| Hiérarchie parent/enfant | ✅ | 80% |
| Statistiques | ✅ | 70% |
| **API Sites** | | |
| CRUD sites | ✅ | 78% |
| GeoJSON import/export | ✅ | 75% |
| Filtres géospatiaux | ⚠️ | 57% |

#### Module Plans (apps/plans)

| Fonctionnalité | Tests | Couverture |
|----------------|-------|------------|
| **Modèles** | | |
| PlanGestion CRUD | ✅ | 75% |
| CorSitePg (multi-sites) | ✅ | 80% |
| CorPgFichier (attachements) | ✅ | 70% |
| **API Plans** | | |
| CRUD plans | ✅ | 59% |
| Assignation sites | ✅ | 100% |
| Endpoint stats | ✅ | 100% |
| Endpoint geojson_list | ✅ | 80% |
| Filtres avancés | ⚠️ | 62% |
| Export GeoJSON | ✅ | 80% |

#### Module Auth (apps/authentication)

| Fonctionnalité | Tests | Couverture |
|----------------|-------|------------|
| Login JWT | ✅ | 94% |
| Refresh token | ✅ | 100% |
| Logout | ⚠️ | 44% (blacklist non activé) |
| Endpoint /me | ✅ | 100% |
| Impersonation | ⚠️ | 44% |

### Frontend - Couverture par module

#### Core Module

| Fonctionnalité | Tests | Couverture |
|----------------|-------|------------|
| **AuthService** | | |
| Login/Logout | ✅ | 74% |
| Token management | ✅ | 80% |
| Role checking | ✅ | 100% |
| Signals (currentUser, etc.) | ✅ | 90% |
| Impersonation | ✅ | 60% |
| **Guards** | | |
| authGuard | ✅ | 100% |
| roleGuard | ✅ | 100% |
| adminGuard | ✅ | 100% |
| guestGuard | ✅ | 100% |
| notAdminOgOnlyGuard | ✅ | 100% |
| **Interceptor** | | |
| Token injection | ✅ | 100% |
| 401 handling | ✅ | 100% |
| Token refresh | ✅ | 100% |

### Légende

- ✅ Bien couvert (>70%)
- ⚠️ Partiellement couvert (40-70%)
- ❌ Non couvert (<40%)

---

## Prochaines étapes

### Priorité Haute

1. **Tests E2E avec Playwright ou Cypress**
   - Parcours utilisateur complet (login → création plan → export)
   - Tests visuels de régression
   - Tests multi-navigateurs

2. **Augmenter couverture backend**
   - ViewSets plans (actuellement 59%)
   - Filtres avancés (actuellement 62%)
   - Endpoints d'impersonation

3. **Tests frontend services**
   - `AdminService` (actuellement 0%)
   - Composants modaux (forms, confirmations)

### Priorité Moyenne

4. **Tests de performance**
   - Benchmarks API avec locust ou k6
   - Tests de charge pour endpoints critiques
   - Profiling requêtes SQL

5. **Tests de sécurité**
   - Tests d'injection SQL
   - Tests XSS
   - Validation CORS
   - Tests de rate limiting

6. **Tests de migration**
   - Vérifier réversibilité des migrations
   - Tests de données avant/après migration

### Priorité Basse

7. **Tests de composants Angular**
   - Composants d'affichage (gauges, icons)
   - Composants de navigation
   - Formulaires réactifs

8. **Documentation automatique**
   - Génération doc API depuis tests
   - Badges de couverture dans README

---

## CI/CD avec GitHub Actions

### Configuration recommandée

Créer le fichier `.github/workflows/tests.yml` :

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  POSTGRES_DB: test_db
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres
  DJANGO_SETTINGS_MODULE: config.settings.development

jobs:
  # ============================================
  # Backend Tests
  # ============================================
  backend-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgis/postgis:15-3.3
        env:
          POSTGRES_DB: ${{ env.POSTGRES_DB }}
          POSTGRES_USER: ${{ env.POSTGRES_USER }}
          POSTGRES_PASSWORD: ${{ env.POSTGRES_PASSWORD }}
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        working-directory: ./backend
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-django pytest-cov factory-boy Faker

      - name: Run migrations
        working-directory: ./backend
        env:
          DATABASE_URL: postgis://${{ env.POSTGRES_USER }}:${{ env.POSTGRES_PASSWORD }}@localhost:5432/${{ env.POSTGRES_DB }}
        run: python manage.py migrate

      - name: Run tests with coverage
        working-directory: ./backend
        env:
          DATABASE_URL: postgis://${{ env.POSTGRES_USER }}:${{ env.POSTGRES_PASSWORD }}@localhost:5432/${{ env.POSTGRES_DB }}
        run: |
          pytest tests/ \
            --cov=apps \
            --cov-report=xml \
            --cov-report=term-missing \
            --junitxml=junit.xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./backend/coverage.xml
          flags: backend
          name: backend-coverage

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: backend-test-results
          path: ./backend/junit.xml

  # ============================================
  # Frontend Tests
  # ============================================
  frontend-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci

      - name: Run tests with coverage
        working-directory: ./frontend
        run: npm run test:coverage -- --ci --reporters=default --reporters=jest-junit

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./frontend/coverage/lcov.info
          flags: frontend
          name: frontend-coverage

      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: frontend-test-results
          path: ./frontend/junit.xml

  # ============================================
  # Linting & Type Checking
  # ============================================
  lint:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Python linters
        run: pip install black isort flake8

      - name: Check Python formatting
        working-directory: ./backend
        run: |
          black --check .
          isort --check-only .

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install frontend dependencies
        working-directory: ./frontend
        run: npm ci

      - name: TypeScript type check
        working-directory: ./frontend
        run: npx tsc --noEmit

  # ============================================
  # Build Check
  # ============================================
  build:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]

    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Build frontend
        working-directory: ./frontend
        run: |
          npm ci
          npm run build:prod
```

### Badges pour README

Ajouter au `README.md` :

```markdown
![Tests](https://github.com/RNF-SI/Cicada/workflows/Tests/badge.svg)
[![codecov](https://codecov.io/gh/RNF-SI/Cicada/branch/main/graph/badge.svg)](https://codecov.io/gh/RNF-SI/Cicada)
```

### Configuration Codecov

Créer `codecov.yml` à la racine :

```yaml
coverage:
  status:
    project:
      default:
        target: 70%
        threshold: 5%
    patch:
      default:
        target: 80%

flags:
  backend:
    paths:
      - backend/
    carryforward: true
  frontend:
    paths:
      - frontend/
    carryforward: true

comment:
  layout: "reach,diff,flags,files"
  behavior: default
  require_changes: true
```

---

## Bonnes pratiques

### Écrire de bons tests

1. **Nommer clairement** : `test_create_user_with_valid_email_succeeds`
2. **Un assert par test** (quand possible)
3. **Arrange-Act-Assert** pattern
4. **Utiliser les factories** au lieu de créer manuellement
5. **Isoler les tests** : chaque test doit pouvoir s'exécuter seul

### Éviter

- Tests qui dépendent de l'ordre d'exécution
- Données de test en dur (utiliser Faker)
- Tests trop larges qui testent plusieurs fonctionnalités
- Mocks excessifs qui ne testent plus rien de réel

### Maintenance

- Exécuter les tests avant chaque commit
- Maintenir la couverture au-dessus de 70%
- Revoir les tests lors des refactorings
- Documenter les tests complexes

---

## Ressources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-django](https://pytest-django.readthedocs.io/)
- [Factory Boy](https://factoryboy.readthedocs.io/)
- [Jest Documentation](https://jestjs.io/)
- [jest-preset-angular](https://thymikee.github.io/jest-preset-angular/)
- [Angular Testing Guide](https://angular.io/guide/testing)
