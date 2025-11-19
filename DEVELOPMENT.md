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

### Gestion des erreurs

```json
# Token expiré (401)
{"detail": "Given token not valid for any token type", "code": "token_not_valid"}

# Token manquant (401)  
{"detail": "Authentication credentials were not provided."}

# Identifiants incorrects (401)
{"detail": "No active account found with the given credentials"}
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

- **`core`** : Modèles partagés (nomenclatures, utilitaires)
- **`users`** : Gestion utilisateurs, organismes, sites
- **`plans`** : Plans de gestion (à venir)
- **`api`** : Endpoints API publics (à venir)

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

## 🚀 Prochaines étapes

### V0 (MVP en cours)
- ✅ Modèles de données et admin
- 🔄 **API REST Django** (prochaine étape)
- ⏳ Authentification JWT
- ⏳ Interface Angular basique

### V1 
- Permissions avancées par rôle
- Workflow de validation
- Exports PDF
- Géolocalisation avancée

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