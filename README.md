# 🌿 Outil Plan de Gestion

Application web de gestion des plans de gestion d'espaces naturels développée pour le **CEN** (Conservatoire d'Espaces Naturels) et **RNF** (Réserves Naturelles de France).

## 🎯 Objectif

Centraliser et standardiser la gestion des plans de gestion des aires protégées françaises avec :
- Gestion des utilisateurs et organismes gestionnaires
- Référencement des sites naturels avec cartographie
- CRUD des plans de gestion multi-sites  
- API publique pour l'interopérabilité
- Interface moderne et intuitive

## 🚀 Installation et lancement rapide

### Prérequis

- [Docker](https://docs.docker.com/get-docker/) (version 20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0+)
- Git

### Installation

1. **Cloner le repository**
   ```bash
   git clone https://github.com/RNF-SI/outil_plan_de_gestion.git
   cd outil_plan_de_gestion
   ```

2. **Configurer l'environnement**
   ```bash
   cp .env.example .env
   # Éditez le fichier .env selon vos besoins
   ```

3. **Lancer l'application**
   ```bash
   docker-compose up -d
   ```

4. **Accéder à l'application**
   - Backend Django API : http://localhost:8000
   - Interface d'administration : http://localhost:8000/admin (login: `admin` / `admin`)
   - Frontend Angular : http://localhost:4200 *(à venir)*

### Commandes essentielles

```bash
# Démarrer l'application
docker-compose up -d

# Arrêter l'application  
docker-compose down

# Voir les logs
docker-compose logs -f

# Reconstruire après modifications
docker-compose build
```

## 🏗️ Architecture

### État actuel du projet

✅ **Implémenté :**
- Modèles de données Django (Users, Organisations, Sites, Plans, Nomenclatures)  
- Interface d'administration Django complète
- Authentification JWT complète avec API REST
- Système de rôles et permissions hiérarchiques
- **Référentiels de nomenclatures standardisés** (28 types, 261 valeurs)
- Middleware de sécurité et audit intégré
- Base de données PostgreSQL avec PostGIS
- Support Docker avec migrations automatiques

🔄 **En cours :**
- API REST CRUD utilisateurs et organismes (prochaine étape)
- Interface Angular (à venir)

### Services Docker

- **web** : Application Django backend (port 8000)
- **frontend** : Application Angular en mode développement (port 4200) *(à venir)*
- **db** : PostgreSQL 15 avec PostGIS (port 5432)
- **redis** : Cache et broker Celery (port 6379)
- **celery** : Worker Celery (optionnel)

### Structure du projet

```
outil_plan_de_gestion/
├── backend/              # Application Django
│   ├── Dockerfile
│   └── docker/
│       └── entrypoint.sh
├── frontend/             # Application Angular
│   └── Dockerfile
├── docker/              # Configuration Docker
│   └── postgres/        # Scripts d'initialisation PostgreSQL
├── docker-compose.yml   # Configuration des services
├── .env.example        # Variables d'environnement exemple
└── README.md
```

## ⚡ Démarrage rapide

1. **Cloner :** `git clone https://github.com/RNF-SI/outil_plan_de_gestion.git`
2. **Lancer :** `docker-compose up -d`  
3. **Accéder :** http://localhost:8000/admin/ (`admin` / `admin`)

L'interface d'administration permet de gérer utilisateurs, organismes, sites et nomenclatures avec des données de test pré-chargées.

### 🔗 API REST

L'API d'authentification JWT est opérationnelle :
- **Login :** `POST /api/auth/login/` avec email/password
- **Token refresh :** `POST /api/auth/refresh/`  
- **User info :** `GET /api/auth/me/`

L'API REST complète est disponible :

**Utilisateurs :**
- **Liste :** `GET /api/users/` (pagination, filtres, recherche)
- **Détail :** `GET /api/users/{id}/` 
- **CRUD :** POST, PUT/PATCH, DELETE avec permissions
- **Actions :** changement mot de passe, assignation sites, statistiques

**Plans de Gestion :**
- **Plans :** `GET /api/plans/plans/` avec filtres avancés et GeoJSON
- **Fichiers :** `POST /api/plans/fichiers/` upload et téléchargement sécurisé
- **Actions :** Assignation sites/référents, statistiques, exports

**Organismes et Sites :**
- **Organismes :** `GET /api/users/organismes/` avec hiérarchie et relations
- **Sites :** `GET /api/users/sites/` avec support GeoJSON complet
- **GeoJSON :** `/sites/geojson_list/` pour cartes interactives
- **Relations :** Assignations organismes ↔ sites ↔ utilisateurs

**Documentation API complète :** 
- **[API_PLANS_GUIDE.md](docs/API_PLANS_GUIDE.md)** - Guide API Plans de Gestion
- **[API_USERS_GUIDE.md](docs/API_USERS_GUIDE.md)** - Guide API Utilisateurs
- **[API_ORGANISMES_SITES_GUIDE.md](docs/API_ORGANISMES_SITES_GUIDE.md)** - Guide API Organismes/Sites
- **[NOMENCLATURES.md](docs/NOMENCLATURES.md)** - Référentiels et nomenclatures

Test avec curl :
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin", "password": "admin"}'
```

## 📖 Documentation

- **[📚 Index Documentation](docs/README.md)** - Index complet de toute la documentation
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Guide technique complet pour développeurs
- **[CLAUDE.md](CLAUDE.md)** - Guide pour Claude Code
- **[claude.md](claude.md)** - Spécifications détaillées du projet

## 🛠️ Technologies

- **Backend** : Django 5.0+, PostgreSQL + PostGIS, Redis
- **Frontend** : Angular 19+ *(à venir)*
- **Infrastructure** : Docker & Docker Compose

## 🤝 Contribution

1. Créer une branche depuis `develop`
2. Faire vos modifications
3. Tester localement
4. Créer une Pull Request vers `develop`

## 📄 Licence

Ce projet est sous licence GPL-3.0. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support

- **Issues** : https://github.com/RNF-SI/outil_plan_de_gestion/issues
- **Project Board** : https://github.com/RNF-SI/outil_plan_de_gestion/projects/1