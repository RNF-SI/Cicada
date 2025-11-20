# 🔧 Guide de développement

Guide technique pour développer sur l'Outil Plan de Gestion.

## 🚀 Installation développeur

### Prérequis

- [Docker](https://docs.docker.com/get-docker/) (version 20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0+)
- Git
- IDE recommandé : VS Code avec extensions Django/Python

### Setup rapide

```bash
# 1. Cloner le projet
git clone https://github.com/RNF-SI/outil_plan_de_gestion.git
cd outil_plan_de_gestion

# 2. Lancer l'environnement de développement
docker-compose up -d

# 3. Accès
# - Admin Django : http://localhost:8000/admin/ (admin / admin)
# - API Django : http://localhost:8000/
```

## 🏗️ Architecture technique

### Structure du projet

```
outil_plan_de_gestion/
├── backend/                    # Application Django
│   ├── apps/                   # Applications Django modulaires
│   │   ├── core/              # Modèles partagés (nomenclatures)
│   │   │   ├── models.py      # TypeNomenclature, Nomenclature
│   │   │   ├── admin.py       # Interface admin
│   │   │   └── migrations/    # Historique BDD
│   │   └── users/             # Gestion utilisateurs/sites
│   │       ├── models.py      # Role, BibOrganismes, Site
│   │       ├── admin.py       # Interface admin géospatiale
│   │       └── migrations/    # Historique BDD
│   ├── config/                # Configuration Django
│   │   ├── settings/          # Settings par environnement
│   │   └── urls.py           # Routes principales
│   ├── create_superuser.py    # Script admin
│   └── create_test_data.py    # Script données test
├── frontend/                  # Application Angular (à venir)
├── docker-compose.yml         # Configuration Docker
└── docs/                     # Documentation
```

### Modèles de données implémentés

#### Users App
- **`Role`** : Utilisateurs avec auth par email (CustomUser)
- **`BibOrganismes`** : Organismes gestionnaires avec hiérarchie
- **`Site`** : Sites naturels avec géométries PostGIS
- **`CorRoleSite`** : Relations utilisateurs ↔ sites
- **`CorOgSite`** : Relations organismes ↔ sites

#### Core App  
- **`TypeNomenclature`** : Types de référentiels
- **`Nomenclature`** : Valeurs de référentiels (hiérarchiques)

## 🔄 Workflow de développement

### Modifications de modèles

```bash
# 1. Modifier models.py
# Exemple : ajouter un champ au modèle Site

# 2. Générer la migration
docker-compose exec web python manage.py makemigrations

# 3. Appliquer en base
docker-compose exec web python manage.py migrate

# 4. Optionnel : mettre à jour admin.py pour le nouveau champ
```

### Django Admin

L'interface admin est automatiquement générée :

**Accès :** http://localhost:8000/admin/ (`admin` / `admin`)

**Customisation :**
```python
# Dans apps/users/admin.py
@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('nom_site', 'surf_off', 'active')  # Colonnes
    list_filter = ('active', 'marin')                  # Filtres
    search_fields = ('nom_site',)                      # Recherche
    readonly_fields = ('id_site',)                     # Lecture seule
```

### Commandes utiles

```bash
# Backend Django
docker-compose exec web python manage.py shell          # Console Django
docker-compose exec web python manage.py makemigrations  # Créer migrations
docker-compose exec web python manage.py migrate        # Appliquer migrations
docker-compose exec web python create_superuser.py      # Créer admin
docker-compose exec web python create_test_data.py      # Données test

# Base de données
docker-compose exec db psql -U outil_user -d outil_plan_gestion  # Console PostgreSQL

# Logs et debug
docker-compose logs -f web      # Logs Django
docker-compose logs -f db       # Logs PostgreSQL
docker-compose ps              # État des services
```

### Tests

```bash
# Tests backend (à implémenter)
docker-compose exec web python manage.py test

# Avec coverage (à configurer)
docker-compose exec web pytest --cov=apps --cov-report=html
```

## 🔐 Authentification JWT

### Configuration

L'application utilise **JWT (JSON Web Tokens)** pour l'authentification API :

```python
# Configuration dans settings/base.py
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),     # Token d'accès : 1h
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),       # Token refresh : 7 jours
    'ROTATE_REFRESH_TOKENS': True,                     # Rotation automatique
    'BLACKLIST_AFTER_ROTATION': True,                  # Blacklist ancien token
    'USER_ID_FIELD': 'id_role',                        # Champ ID utilisateur
}
```

### Endpoints d'authentification

```bash
# Connexion (email + password → tokens JWT)
POST /api/auth/login/
Content-Type: application/json
{"email": "admin", "password": "admin"}

# Réponse
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 4,
    "email": "admin",
    "nom": "admin",
    "is_staff": true,
    "organisme": null
  }
}
```

```bash
# Renouvellement du token d'accès
POST /api/auth/refresh/
Content-Type: application/json
{"refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."}
```

```bash
# Informations utilisateur connecté
GET /api/auth/me/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

```bash
# Déconnexion (blacklist du refresh token)
POST /api/auth/logout/
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
Content-Type: application/json
{"refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."}
```

### Usage dans le code

**Vues protégées par défaut :**
```python
# Toutes les vues API sont protégées par défaut
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def protected_view(request):
    # request.user est automatiquement disponible
    user = request.user
    return Response({'user_id': user.id_role})
```

**Vues publiques :**
```python
from rest_framework.decorators import api_view, permission_classes

@api_view(['GET'])
@permission_classes([])  # Aucune permission requise
def public_view(request):
    return Response({'status': 'public'})
```

**Test avec script automatisé :**
```bash
# Script de test complet de l'API JWT
docker-compose exec web python test_auth_api.py
```

**Test avec curl :**
```bash
# 1. Obtenir un token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin", "password": "admin"}' \
  | jq -r '.access')

# 2. Utiliser le token
curl -X GET http://localhost:8000/api/auth/me/ \
  -H "Authorization: Bearer $TOKEN"
```

## 👥 API REST Utilisateurs

### Endpoints disponibles

L'API REST pour la gestion des utilisateurs est complètement opérationnelle :

**Endpoints principaux :**
- `GET /api/users/` : Liste paginée avec filtres et recherche
- `GET /api/users/{id}/` : Détail utilisateur avec permissions
- `POST /api/users/` : Création avec validation métier
- `PUT/PATCH /api/users/{id}/` : Modification sécurisée
- `DELETE /api/users/{id}/` : Soft delete

**Actions spécialisées :**
- `GET /api/users/me/` : Profil utilisateur connecté
- `POST /api/users/{id}/change-password/` : Changement mot de passe
- `POST /api/users/{id}/assign-site/` : Assignation sites
- `GET /api/users/stats/` : Statistiques (admin)

### Fonctionnalités

**Pagination :** 20 résultats/page (configurable), métadonnées complètes

**Filtres :** 15+ filtres disponibles (search, role_level, organisme, dates, etc.)

**Sécurité :** Permissions granulaires, filtrage automatique selon rôle

**Documentation complète :** Voir `backend/API_USERS_GUIDE.md`

## 🏢 API REST Organismes et Sites

### Endpoints disponibles

L'API REST pour la gestion des organismes et sites avec support GeoJSON est opérationnelle :

**Organismes :**
- `GET /api/users/organismes/` : Liste paginée avec filtres
- `GET /api/users/organismes/{id}/` : Détail complet avec relations
- `POST /api/users/organismes/` : Création avec validation
- `PATCH /api/users/organismes/{id}/` : Modification sécurisée
- `POST /api/users/organismes/{id}/assign_site/` : Assignation site
- `POST /api/users/organismes/{id}/bulk_assign_sites/` : Assignation en masse

**Sites :**
- `GET /api/users/sites/` : Liste paginée avec filtres géospatiaux
- `GET /api/users/sites/{id}/` : Détail complet avec géométries
- `GET /api/users/sites/{id}/geojson/` : Format GeoJSON Feature
- `GET /api/users/sites/geojson_list/` : FeatureCollection GeoJSON
- `POST /api/users/sites/` : Création avec support GeoJSON
- `POST /api/users/sites/{id}/assign_user/` : Assignation utilisateur

### Fonctionnalités avancées

**Support GeoJSON :** Import/Export automatique PostGIS ↔ GeoJSON

**Relations :** Gestion complète organismes ↔ sites ↔ utilisateurs

**Bulk operations :** Assignations en masse avec gestion des permissions

**Nested routes :** `/organismes/{id}/sites/` pour navigation hiérarchique

**Filtres géospatiaux :** Surface, géométries, localisation

**Documentation complète :** Voir `backend/API_ORGANISMES_SITES_GUIDE.md`

### Test rapide

```bash
# 1. Obtenir token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin", "password": "admin"}' | jq -r '.access')

# 2. Lister utilisateurs
curl -X GET http://localhost:8000/api/users/ \
  -H "Authorization: Bearer $TOKEN" | jq

# 3. Lister organismes
curl -X GET http://localhost:8000/api/users/organismes/ \
  -H "Authorization: Bearer $TOKEN" | jq

# 4. Lister sites avec GeoJSON
curl -X GET http://localhost:8000/api/users/sites/geojson_list/ \
  -H "Authorization: Bearer $TOKEN" | jq

# 5. Statistiques
curl -X GET http://localhost:8000/api/users/sites/stats/ \
  -H "Authorization: Bearer $TOKEN" | jq
```

### Gestion des erreurs

```json
# Token expiré (401)
{"detail": "Given token not valid for any token type", "code": "token_not_valid"}

# Token manquant (401)  
{"detail": "Authentication credentials were not provided."}

# Identifiants incorrects (401)
{"detail": "No active account found with the given credentials"}
```

## 🔐 Système de rôles et permissions

### Configuration

L'application utilise un **système de rôles hiérarchiques** avec des permissions granulaires :

```python
# 4 niveaux de rôles dans le modèle Role
ROLE_CHOICES = [
    ('utilisateur', 'Utilisateur'),      # Lecture seule
    ('referent', 'Référent'),           # Gestion sites assignés
    ('admin_og', 'Administrateur OG'),   # Gestion organisme
    ('super_admin', 'Super Admin'),      # Accès total
]
```

### Rôles et permissions

| Rôle | Permissions | Scope |
|------|-------------|-------|
| **Super Admin** | Toutes permissions | Global |
| **Admin Organisme** | CRUD organisme + sites + utilisateurs | Son organisme |
| **Référent** | CRUD sites assignés | Sites spécifiques |
| **Utilisateur** | Lecture seule | Données visibles |

### Types de permissions

**Django standard :** `{action}_{model}` (add_role, change_site, view_organisme, delete_user)

**Personnalisées métier :**

| Permission | Description | Qui l'a |
|------------|-------------|---------|
| `view_all_users` | Voir tous les utilisateurs | Super Admin |
| `manage_organisme_users` | Gérer users de son organisme | Admin Organisme+ |
| `view_all_organismes` | Voir tous les organismes | Super Admin |
| `manage_own_organisme` | Gérer son organisme | Admin Organisme+ |
| `view_all_sites` | Voir tous les sites | Super Admin |
| `manage_organisme_sites` | Gérer sites de son organisme | Admin Organisme+ |
| `manage_assigned_sites` | Gérer sites assignés | Référent+ |
| `access_admin_interface` | Accès interface admin | Référent+ |
| `export_data` | Exporter des données | Référent+ |
| `import_data` | Importer des données | Admin Organisme+ |

### Groupes Django automatiques

```bash
# Commande pour créer/synchroniser les permissions
docker-compose exec web python manage.py create_permissions

# Groupes créés automatiquement :
# - Super Administrateurs (30 permissions)
# - Administrateurs Organisme (19 permissions)  
# - Référents (9 permissions)
# - Utilisateurs (5 permissions)
```

### Usage dans les vues API

**Permissions DRF (classes) :**
```python
from apps.users.permissions import IsSuperAdmin, IsAdminOrganisme

@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def admin_only_view(request):
    return Response({'message': 'Accès admin OK'})
```

**Décorateurs (fonctions) :**
```python
from apps.users.decorators import require_admin_organisme

@api_view(['GET'])
@require_admin_organisme
def admin_view(request):
    return Response({'message': 'Accès admin OK'})
```

**Vérifications dans le modèle :**
```python
# Sur un objet Role
user.is_super_admin()           # True/False
user.can_manage_organisme(org)  # True/False  
user.can_manage_site(site)      # True/False
```

### Middleware de sécurité

**3 middleware personnalisés actifs :**

1. **SecurityHeadersMiddleware** : Ajoute headers sécurité (anti-XSS, etc.)
2. **PermissionMiddleware** : Ajoute headers d'info utilisateur
3. **AuditMiddleware** : Log des actions importantes

```bash
# Headers automatiques dans les réponses API :
X-User-Role: super_admin
X-User-Organisme: 1
X-User-Permissions: {"is_super_admin": true, ...}
```

### Test du système

```bash
# Test complet des permissions
docker-compose exec web python test_permissions.py

# Test des API de permissions
docker-compose exec web python test_permissions_api.py
```

### Endpoints de test disponibles

```bash
# Permissions DRF
GET /api/users/test/super-admin/           # Super admin seulement
GET /api/users/test/admin-organisme/       # Admin organisme+
GET /api/users/test/referent/              # Référent+

# Décorateurs
GET /api/users/test/decorator-super-admin/
GET /api/users/test/decorator-admin-organisme/
GET /api/users/test/decorator-referent/

# Permissions d'objet
GET /api/users/organismes/<id>/            # Vérifie accès organisme
GET /api/users/sites/<id>/                 # Vérifie accès site

# Informations utilisateur
GET /api/users/permissions/               # Infos permissions user
```

### Référence rapide développeurs

**Vérifier permission dans le code :**
```python
# Méthodes du modèle Role
user.is_super_admin()                    # True/False
user.can_manage_organisme(organisme)     # True/False  
user.can_manage_site(site)               # True/False

# Permissions Django standard
user.has_perm('users.add_role')          # True/False
user.has_perm('users.export_data')       # True/False

# Dans les vues DRF
@permission_classes([IsSuperAdmin])
@require_admin_organisme  # Décorateur

# Dans les templates
{% if perms.users.add_site %}...{% endif %}
```

**Permissions par groupe :**
- **Super Admin** : 30 permissions (toutes)
- **Admin Organisme** : 19 permissions (son organisme)  
- **Référent** : 9 permissions (sites assignés)
- **Utilisateur** : 5 permissions (lecture seule)

### Sécurité intégrée

**Protection automatique :**
- Toutes les API protégées par défaut (sauf `/api/auth/`)
- Vérification compte actif (`user.active = True`)
- Headers de sécurité sur toutes les réponses
- Audit automatique des actions CRUD

**Gestion des erreurs :**
```json
# Accès refusé (403)
{"error": "Permissions Super Administrateur requises"}

# Compte désactivé (403)  
{"error": "Compte utilisateur désactivé", "code": "account_disabled"}

# Organisme non autorisé (403)
{"error": "Accès non autorisé à cet organisme"}
```

## 🛡️ Middleware Django

### Qu'est-ce qu'un middleware ?

Un **middleware** est un composant qui s'exécute entre la requête HTTP et la réponse, permettant de traiter/modifier les données à différents moments du cycle de vie d'une requête.

```
Requête HTTP → MW1 → MW2 → MW3 → Vue Django → MW3 → MW2 → MW1 → Réponse HTTP
```

### Rôle des middleware

**Traitement global :** Actions qui s'appliquent à **toutes** les requêtes
- **Sécurité :** Authentification, CORS, protection CSRF
- **Logging/Audit :** Enregistrer qui fait quoi et quand  
- **Headers :** Ajouter des en-têtes de sécurité
- **Performance :** Cache, compression, monitoring

### Middleware personnalisés du projet

**1. SecurityHeadersMiddleware :**
```python
# Ajoute des en-têtes de sécurité à toutes les réponses
response['X-Content-Type-Options'] = 'nosniff'  # Anti-XSS
response['X-Frame-Options'] = 'DENY'            # Anti-iframe  
response['X-XSS-Protection'] = '1; mode=block'  # Protection XSS
```

**2. PermissionMiddleware :**
```python
# Ajoute des informations utilisateur dans les en-têtes
response['X-User-Role'] = request.user.role_level
response['X-User-Organisme'] = str(request.user.id_organisme.id_organisme)
response['X-User-Permissions'] = json.dumps({
    'is_super_admin': request.user.is_super_admin(),
    'is_admin_organisme': request.user.is_admin_organisme(),
})
```

**3. AuditMiddleware :**
```python
# Enregistre les actions importantes pour l'audit
request.audit_info = {
    'user_id': request.user.id_role,
    'action': request.method,  # POST, PUT, DELETE
    'path': request.path,      # /api/users/123/
    'timestamp': datetime.now()
}
```

### Middleware vs Décorateurs

| Middleware | Décorateurs |
|------------|-------------|
| **Toutes** les vues automatiquement | Vue par vue manuellement |
| Configuration centrale | Répétition de code |
| Ordre d'exécution fixe | Flexibilité fine |
| Headers globaux | Logique spécifique |
| Performance globale | Performance ciblée |

**Exemple concret :**
```python
# ✅ Middleware : Headers de sécurité sur TOUTES les réponses
class SecurityHeadersMiddleware:
    def process_response(self, request, response):
        response['X-Frame-Options'] = 'DENY'  # Toutes les réponses !
        return response

# ✅ Décorateur : Permission spécifique à UNE vue
@require_super_admin
def delete_all_users(request):  # Une seule vue
    return Response({'deleted': 'all'})
```

## 🎯 Concepts Django clés

### Migrations

Les migrations Django tracent automatiquement les changements de schéma :

- **Chaque app** a son dossier `migrations/`
- **Dépendances** entre apps gérées automatiquement
- **Ordre d'application** respecté (ex: `core` avant `users`)

### Admin Interface

Django génère automatiquement une interface d'administration :

- **Enregistrement simple :** `admin.site.register(Model)`
- **Customisation avancée :** Classes `ModelAdmin` personnalisées  
- **Relations inline :** Édition de relations dans le même écran
- **Géospatial :** Cartes automatiques pour les champs géographiques

### Apps Django

Organisation modulaire :

- **`core`** : Modèles partagés (nomenclatures, utilitaires) ✅
- **`users`** : Gestion utilisateurs, organismes, sites ✅
- **`authentication`** : Gestion JWT et auth ✅
- **`plans`** : Plans de gestion (Issue #18-21 à venir)
- **`api`** : Endpoints API publics (Issue #22-23 à venir)

## 🔒 Sécurité & Bonnes pratiques

### Développement

1. **Jamais de données sensibles** dans le code (utilisez `.env`)
2. **Migrations irréversibles** : testez avant production
3. **Backup BDD** avant migrations majeures
4. **Git** : commits atomiques avec messages clairs

### Base de données

1. **PostGIS** pour toutes les opérations géospatiales
2. **Indexes** sur les champs recherchés fréquemment  
3. **Transactions** pour les opérations critiques
4. **Soft delete** pour les données importantes

### Django

1. **CRUD permissions** basées sur les rôles utilisateur
2. **Validation** côté modèle ET formulaire
3. **Sanitization** des entrées utilisateur
4. **Rate limiting** sur les API (à venir)

## 📊 Données de test

Le projet inclut des données de test réalistes :

```bash
# Créer les données
docker-compose exec web python create_test_data.py
```

**Contenu :**
- **3 organismes** : RNF, CEN Auvergne-Rhône-Alpes, DREAL
- **3 sites** : Camargue, Aiguilles Rouges, Grand-Voyeux
- **5 types sites** : RNN, RNR, PNR, ENS (nomenclatures)
- **3 utilisateurs** : admin + 2 utilisateurs test

## 🔍 Debugging

### Django Debug Toolbar (à ajouter)

```python
# En développement, pour analyser les performances
# Affiche requêtes SQL, temps d'exécution, etc.
```

### Logs Django

```bash
# Logs en temps réel
docker-compose logs -f web

# Niveau DEBUG dans settings/development.py
DEBUG = True
```

### Base de données

```bash
# Console PostgreSQL
docker-compose exec db psql -U outil_user -d outil_plan_gestion

# Vérifier les tables
\dt

# Voir la structure d'une table
\d t_roles
```

## 🚀 Roadmap et prochaines étapes

### État d'avancement basé sur GitHub Issues

**✅ Phase 1-infrastructure (Terminée)**
- ✅ #6 - Initialisation du projet Django
- ✅ #7 - Configuration Docker et docker-compose 
- ✅ #8 - Configuration PostgreSQL avec PostGIS

**✅ Phase 2-auth (Partiellement terminée)**
- ✅ #12 - Système de rôles et permissions
- ✅ #14 - Modèles de données Utilisateurs/Organismes/Sites
- ⏳ #10 - Authentification interne Django (en cours - JWT implémenté)

**✅ Phase 3-users (Partiellement terminée)**
- ✅ #15 - API REST Utilisateurs
- ✅ #16 - API REST Organismes et Sites
- 🔄 **#17 - Interface Admin Django personnalisée** (prochaine étape)
- ⏳ #13 - Formulaire d'onboarding utilisateur
- ⏳ #38 - Keycloak: lien avec les tables Utilisateurs et Organisme

**⏳ Phase 4-core (À venir - Plans de gestion)**
- #18 - Modèles de données Plans de Gestion
- #19 - API REST Plans de Gestion
- #21 - Permissions spécifiques aux PG
- #20 - Workflow de validation des PG

**⏳ Phase 5-frontend (À venir - Interface Angular)**
- #26 - Initialisation du projet Angular
- #27 - Module d'authentification Angular
- #37 - Interface d'accueil
- #22 - Système de gestion des tokens API
- #23 - Endpoints API publics

**⏳ Phase 6-release (À venir - Finalisation)**
- #28 - Dashboard utilisateur
- #29 - Module de gestion basique des PG
- #30 - Documentation technique
- #31 - Tests unitaires backend
- #32 - Tests frontend Angular
- #35 - Audit de sécurité (P0-critical)
- #36 - RGPD Compliance (P0-critical)

### 🎯 Prochaine priorité recommandée

**Issue #17 - Interface Admin Django personnalisée**
- **Phase**: 3-users (finaliser la gestion utilisateurs)
- **Priorité**: P1-important  
- **Taille**: S (2h-1 jour)
- **Objectif**: Personnaliser l'admin Django avec actions en masse, filtres avancés, exports

### 📋 Séquence logique suivante

1. **#17** - Interface Admin Django personnalisée (finaliser phase 3-users)
2. **#13** - Formulaire d'onboarding utilisateur (compléter auth)
3. **#18** - Modèles de données Plans de Gestion (démarrer phase 4-core)
4. **#19** - API REST Plans de Gestion (cœur métier)
5. **#21** - Permissions spécifiques aux PG
6. **#26** - Initialisation du projet Angular (démarrer frontend)

### 🔍 Issues critiques P0
- **#10** - Authentification interne Django (JWT déjà implémenté, à finaliser)
- **#35** - Audit de sécurité  
- **#36** - RGPD Compliance

### 📊 Métriques d'avancement
- **Issues fermées**: 7/46 (15%)
- **Phase 1 (Infrastructure)**: 3/3 terminées (100%)
- **Phase 2 (Auth)**: 2/3 terminées (67%) 
- **Phase 3 (Users)**: 2/5 terminées (40%)
- **Phases 4-6**: 0% (à venir)

## 📚 Ressources

- **Django Documentation** : https://docs.djangoproject.com/
- **Django Admin** : https://docs.djangoproject.com/en/5.0/ref/contrib/admin/
- **PostGIS Django** : https://docs.djangoproject.com/en/5.0/ref/contrib/gis/
- **Docker Compose** : https://docs.docker.com/compose/

## 🤝 Contribution

1. **Branch** depuis `develop`
2. **Commits** atomic avec messages clairs
3. **Tests** pour nouvelles fonctionnalités  
4. **PR** vers `develop` avec description
5. **Review** par un pair avant merge

---

Pour les **spécifications métier** complètes, voir `claude.md`  
Pour l'**utilisation Claude Code**, voir `CLAUDE.md`