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

| Stack | Framework | Tests | Couverture | Type |
|-------|-----------|-------|------------|------|
| Backend | pytest + pytest-django | 317 | 62% | Unitaires + Intégration |
| Frontend | Jest + jest-preset-angular | 55 | 10% global, 100% auth | Unitaires |
| **E2E** | **Playwright** | **~80** | **Voir détail ci-dessous** | **End-to-End** |
| **Total** | - | **~452** | - | - |

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
├── frontend/
│   ├── jest.config.js             # Configuration Jest
│   ├── setup-jest.ts              # Setup environnement
│   ├── tsconfig.spec.json         # TypeScript pour tests
│   └── src/app/core/
│       ├── services/
│       │   └── auth.service.spec.ts
│       ├── guards/
│       │   └── auth.guard.spec.ts
│       └── interceptors/
│           └── auth.interceptor.spec.ts
│
└── frontend/e2e/                  # Tests E2E Playwright
    ├── playwright.config.ts       # Configuration Playwright
    ├── global-setup.ts            # Attente services + seed données
    ├── fixtures/
    │   ├── auth.setup.ts          # Login des 6 utilisateurs de test
    │   └── auth.fixture.ts        # Pages pré-authentifiées par rôle
    ├── helpers/
    │   ├── api.helper.ts          # Appels API directs
    │   └── wait.helper.ts         # Utilitaires d'attente
    ├── pages/                     # Page Objects (11 fichiers)
    └── tests/
        ├── auth/                  # Login, logout, register (13 tests)
        ├── admin/                 # Users, sites, validations, etc. (46 tests)
        ├── access/                # Contrôle d'accès par rôle (13 tests)
        └── navigation/            # Navigation et header (4 tests)
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
docker compose exec web pytest tests/

# Tous les tests avec couverture
docker compose exec web pytest tests/ --cov=apps --cov-report=html

# Tests unitaires uniquement
docker compose exec web pytest tests/ -m unit

# Tests d'intégration uniquement
docker compose exec web pytest tests/ -m integration

# Un fichier spécifique
docker compose exec web pytest tests/integration/test_api_users.py -v

# Un test spécifique
docker compose exec web pytest tests/integration/test_api_users.py::TestUsersListEndpoint::test_list_super_admin_sees_all -v

# Mode verbose avec détails d'erreur
docker compose exec web pytest tests/ -v --tb=long
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

## E2E (Playwright)

### Outils utilisés

| Outil | Version | Usage |
|-------|---------|-------|
| @playwright/test | 1.49+ | Framework E2E |
| Chromium | (bundled) | Navigateur de test |

### Prérequis

Les tests E2E s'exécutent contre le stack Docker réel (Django + PostgreSQL + Redis + Angular).

```bash
# 1. Démarrer les services Docker
docker compose up -d

# 2. S'assurer que les données de test existent
docker compose exec web python manage.py seed_testdata
```

### Exécution

```bash
cd frontend

# Tous les tests (headless)
npm run e2e

# Interface visuelle Playwright
npm run e2e:ui

# Tests visibles dans le navigateur
npm run e2e:headed

# Mode debug avec inspector
npm run e2e:debug

# Générer des tests via enregistrement
npm run e2e:codegen
```

### Architecture

#### Authentification (storageState)

Les tests utilisent le mécanisme `storageState` de Playwright : un projet `auth-setup` se connecte via l'UI pour 6 utilisateurs de test et sauvegarde les tokens JWT dans des fichiers `.auth/*.json`. Les tests suivants réutilisent ces fichiers sans se reconnecter.

| Utilisateur | Email | Rôle | Fichier storageState |
|-------------|-------|------|---------------------|
| Super Admin | `admin@test.fr` | super_admin | `super-admin.json` |
| Admin RNF | `admin.rnf@test.fr` | admin_og | `admin-rnf.json` |
| Admin CEN | `admin.cen@test.fr` | admin_og | `admin-cen.json` |
| Référent | `referent.camargue@test.fr` | referent | `referent.json` |
| User RNF | `user.rnf@test.fr` | utilisateur | `user-rnf.json` |
| User CEN | `user.cen@test.fr` | utilisateur | `user-cen.json` |

**Mot de passe commun** : `Test123!`

#### Fixture custom (pages pré-authentifiées)

```typescript
// Usage dans les tests :
test('admin voit le dashboard', async ({ superAdminPage }) => {
  await superAdminPage.goto('/administration/dashboard');
});

test('admin RNF ne voit que ses users', async ({ adminRnfPage }) => {
  await adminRnfPage.goto('/administration/utilisateurs');
});
```

Chaque page a son propre contexte navigateur. On peut donc tester des workflows multi-utilisateurs sans impersonation.

#### Page Objects

| Page Object | Fichier | Description |
|-------------|---------|-------------|
| `LoginPage` | `login.page.ts` | Formulaire de connexion |
| `RegisterPage` | `register.page.ts` | Formulaire d'inscription |
| `HomePage` | `home.page.ts` | Page d'accueil avec tuiles |
| `ProfilePage` | `profile.page.ts` | Page profil utilisateur |
| `AdminLayoutPage` | `admin-layout.page.ts` | Sidebar admin + navigation |
| `AdminUsersPage` | `admin-users.page.ts` | Tableau des utilisateurs |
| `AdminSitesPage` | `admin-sites.page.ts` | Tableau des sites |
| `AdminValidationsPage` | `admin-validations.page.ts` | Tableau des validations |
| `AdminOrganismesPage` | `admin-organismes.page.ts` | Grille/détail organismes |
| `AdminDashboardPage` | `admin-dashboard.page.ts` | Dashboard statistiques |
| `SitesListPage` | `sites-list.page.ts` | Liste publique des sites |

### Couverture E2E par fonctionnalité

| Catégorie | Fichier | Tests | Fonctionnalités couvertes |
|-----------|---------|-------|--------------------------|
| **Auth** | `login.spec.ts` | 5 | Login valide, identifiants invalides, champs vides, returnUrl, lien inscription |
| **Auth** | `logout.spec.ts` | 3 | Suppression tokens, redirection, bouton menu |
| **Auth** | `register.spec.ts` | 5 | Inscription valide, validation, password mismatch, email doublon |
| **Admin Users** | `users-list.spec.ts` | 6 | Liste complète, scope organisme, recherche, filtres rôle/statut |
| **Admin Users** | `users-actions.spec.ts` | 5 | Activation/désactivation, assign site, impersonation |
| **Admin Users** | `users-sites.spec.ts` | 4 | Site chips, assign modal, référent badge, plan chips |
| **Admin Sites** | `sites-list.spec.ts` | 5 | Liste, recherche, filtre type, colonnes, résumé |
| **Admin Sites** | `sites-crud.spec.ts` | 5 | Bouton ajout, modal création, validation, rôle-based |
| **Admin Sites** | `sites-orgs.spec.ts` | 3 | Org chips, assign org, user chips |
| **Admin** | `validations.spec.ts` | 6 | Liste, filtres statut/type, approbation, détail, état vide |
| **Admin** | `validation-workflow.spec.ts` | 8 | **Workflow multi-utilisateurs complet** : création demande → vue admin → approbation/rejet → vérification statut |
| **Admin** | `organismes.spec.ts` | 4 | Grille, détail admin_og, recherche, modal édition |
| **Admin** | `dashboard.spec.ts` | 3 | Accès, stats cards, message bienvenue |
| **Accès** | `role-access.spec.ts` | 8 | Accès super_admin, admin_og, référent, utilisateur, guest |
| **Accès** | `data-scope.spec.ts` | 5 | Scope données RNF, CEN, super admin, référent |
| **Navigation** | `navigation.spec.ts` | 4 | Header, sidebar rôle, items masqués, navigation sans erreur |
| **Total** | **17 fichiers** | **~80** | |

### Workflow de validation multi-utilisateurs

Le test `validation-workflow.spec.ts` vérifie le flux complet sans utiliser l'impersonation :

```
1. userRnfPage (utilisateur) → crée une demande d'accès site via API
2. userRnfPage (utilisateur) → vérifie la demande sur /mes-demandes (statut "en attente")
3. superAdminPage (admin)    → vérifie la demande sur /admin/validations
4. superAdminPage (admin)    → approuve la demande
5. userRnfPage (utilisateur) → vérifie le statut "approuvé"
6. superAdminPage (admin)    → vérifie dans l'historique des validations
```

Un second scénario teste le **rejet** avec un motif, en utilisant `userCenPage` et `superAdminPage`.

### Rapports

Les tests génèrent :
- **Rapport HTML** : `frontend/playwright-report/` (ouvrable localement)
- **JUnit XML** : `frontend/e2e-results.xml` (pour CI/CD)
- **Screenshots** : `frontend/test-results/` (captures en cas d'échec)
- **Traces** : Enregistrement vidéo + trace réseau en cas de retry

---

## Prochaines étapes

### Priorité Haute

1. ~~**Tests E2E avec Playwright ou Cypress**~~ ✅ Fait (Playwright, ~80 tests)

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

### Workflow actuel (`.github/workflows/tests.yml`)

Le workflow se déclenche sur :
- Push vers `main` ou `develop`
- Pull request vers `main` ou `develop`
- Push d'un tag `v*` (releases)
- Déclenchement manuel (`workflow_dispatch`)

### Jobs

| Job | Dépendance | Description |
|-----|------------|-------------|
| `backend-tests` | - | pytest avec PostgreSQL/PostGIS |
| `frontend-tests` | - | Jest (unitaires Angular) |
| `typecheck` | - | TypeScript `--noEmit` |
| `e2e-tests` | `backend-tests` | **Playwright avec stack Docker complet** |
| `build` | backend + frontend + typecheck | Build production Angular |
| `email-tests` | - | Tests email Mailpit (workflow_dispatch uniquement) |

### Job E2E détaillé

Le job `e2e-tests` :
1. Démarre les services Docker (db, redis, web)
2. Attend le health check backend (`/api/auth/health/`)
3. Seed les données de test (`seed_testdata`)
4. Installe Playwright + Chromium
5. Démarre le dev server Angular
6. Exécute les tests Playwright
7. Upload le rapport HTML + JUnit en artifact (14 jours de rétention)

**Artefacts CI** : Le rapport Playwright est consultable dans l'onglet "Artifacts" de chaque run GitHub Actions.

### Tests de packaging (hors CI)

Les tests de packaging valident l'installation et la mise à jour du package Debian (`.deb`). Ils sont **exclus de la CI** pour deux raisons :
1. **Hyperviseur requis** : le test VM utilise Multipass, qui nécessite KVM/QEMU — incompatible avec les runners GitHub Actions
2. **Durée** : 10-20 min par exécution, inapproprié pour un pipeline déclenché à chaque push

**Quand les lancer** : uniquement avant de publier un nouveau package `.deb` (release), pour valider que le mécanisme d'upgrade fonctionne.

| Script | Environnement | Durée | Ce qu'il teste |
|--------|--------------|-------|----------------|
| `test-install-quick.sh` | Conteneur Docker | ~30s | Fichiers installés aux bons emplacements |
| `test-install.sh` | Conteneur Docker | ~5 min | Fichiers + services systemd + heartbeat |
| `test-install-web.sh` | Conteneur Docker | ~5 min | Interface web Flask (http://localhost:4567) |
| `test-install-full.sh` | Conteneur Docker | ~10 min | Installation complète avec systemd |
| `test-install-web-full.sh` | Conteneur Docker | ~10 min | Interface web + Docker fonctionnel |
| **`test-upgrade-vm.sh`** | **VM Multipass** | **10-20 min** | **Upgrade v1→v2 : postinst, .env, systemd, docker compose** |

```bash
cd packaging

# Prérequis pour le test VM
sudo snap install multipass

# Test d'upgrade complet (adapter les versions)
./test-upgrade-vm.sh --from 0.1.12 --to 0.1.13

# Relancer rapidement (réutilise la VM)
./test-upgrade-vm.sh --skip-install --from 0.1.12 --to 0.1.13

# Nettoyer
./test-upgrade-vm.sh --cleanup
```

Documentation détaillée : [`packaging/TESTING.md`](../packaging/TESTING.md)

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
