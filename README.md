# 🌿 CICADA

**CICADA** - Application web de gestion des plans de gestion d'espaces naturels développée pour le **CEN** (Conservatoire d'Espaces Naturels) et **RNF** (Réserves Naturelles de France).

> 📄 Pour une présentation détaillée du projet, consultez le document [Présentation_projet_CICADA_VF.pdf](docs/Présentation_projet_CICADA_VF.pdf), qui contient davantage d'informations sur le contexte, les objectifs et le périmètre fonctionnel.

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
   git clone https://github.com/RNF-SI/Cicada.git
   cd Cicada
   ```

2. **(Optionnel) Configurer l'environnement**
   ```bash
   cp .env.example .env
   # Éditez le fichier .env pour personnaliser ports, mots de passe, etc.
   ```
   > Les valeurs par défaut permettent de démarrer sans `.env` en développement.

3. **Lancer l'application**
   ```bash
   docker compose up -d
   ```

4. **Attendre l'initialisation** (~30 secondes pour les migrations)
   ```bash
   docker compose logs -f web
   # Attendre "Starting development server at http://0.0.0.0:8000/"
   ```

5. **Accéder à l'application**
   - Backend Django API : http://localhost:8000
   - Interface d'administration : http://localhost:8000/admin (login: `admin` / `admin`)
   - Frontend Angular : http://localhost:4200
   - **Mailpit** (emails de test) : http://localhost:8025

### Commandes essentielles

```bash
# Démarrer l'application
docker compose up -d

# Arrêter l'application
docker compose down

# Voir les logs
docker compose logs -f

# Reconstruire après modifications
docker compose build
```

### Configuration des variables d'environnement

Le fichier `.env` est **optionnel en développement** grâce aux valeurs par défaut cohérentes définies dans `docker compose.yml`.

#### Valeurs par défaut (sans .env)

| Variable | Valeur par défaut | Description |
|----------|-------------------|-------------|
| `POSTGRES_DB` | `cicada` | Nom de la base de données |
| `POSTGRES_USER` | `cicada_user` | Utilisateur PostgreSQL |
| `POSTGRES_PASSWORD` | `cicada_password` | Mot de passe PostgreSQL |
| `DJANGO_PORT` | `8000` | Port du backend |
| `FRONTEND_PORT` | `4200` | Port du frontend |
| `REDIS_PASSWORD` | `redis_password` | Mot de passe Redis |

#### Quand utiliser un fichier .env ?

- **Développement local** : Pas nécessaire, les défauts fonctionnent
- **Personnalisation** : Pour changer les ports ou mots de passe
- **Production** : **Obligatoire** - utilisez des mots de passe sécurisés et `DEBUG=False`

Pour personnaliser :
```bash
cp .env.example .env
# Éditez .env selon vos besoins
```

> ⚠️ **Production** : Ne jamais utiliser les valeurs par défaut. Générez des mots de passe forts et une nouvelle `SECRET_KEY`.

### Sécurité

Les identifiants présents dans ce dépôt (docker-compose.yml, .env.example) sont **exclusivement destinés au développement local**. Pour tout déploiement en production :

- Générez une nouvelle `SECRET_KEY` Django (ex: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- Définissez des mots de passe forts pour PostgreSQL et Redis
- Configurez `DEBUG=False` et `ALLOWED_HOSTS` correctement
- Utilisez HTTPS et configurez les en-têtes de sécurité
- Ne réutilisez jamais les valeurs par défaut de développement

## 🏗️ Architecture

### État actuel du projet (v0.1.25)

- Backend Django complet : API REST (utilisateurs, organismes, sites, plans, enjeux, opérations, suivis)
- Frontend Angular 19 avec Design System custom (Kit UI CICADA)
- Authentification JWT, rôles hiérarchiques, permissions objet
- Référentiels INPN intégrés : nomenclatures, TaxRef, HabRef, CAMPanule
- Cycle de vie des plans : brouillon, validé, archivé, évaluation mi-parcours
- Notifications, validations, historique d'activité
- Inscription publique avec workflow de validation
- Import en masse de sites (GeoJSON/CSV)
- Package Debian (.deb) avec installeur web et mise à jour automatique
- PostgreSQL 17 + PostGIS, Redis, Celery

### Services Docker

- **web** : Application Django backend (port 8000)
- **frontend** : Application Angular en mode développement (port 4200)
- **db** : PostgreSQL 17 avec PostGIS 3.5 (port 5432)
- **redis** : Cache et broker Celery (port 6379)
- **celery-worker** : Worker Celery pour tâches asynchrones (emails, etc.)
- **celery-beat** : Planificateur de tâches périodiques
- **mailpit** : Serveur SMTP de test - capture les emails (port 8025)

### Structure du projet

```
Cicada/
├── backend/              # Application Django
│   ├── Dockerfile
│   └── docker/
│       └── entrypoint.sh
├── frontend/             # Application Angular
│   └── Dockerfile
├── docker/              # Configuration Docker
│   └── postgres/        # Scripts d'initialisation PostgreSQL
├── docker compose.yml   # Configuration des services
├── .env.example        # Variables d'environnement exemple
└── README.md
```

## ⚡ Démarrage rapide

1. **Cloner :** `git clone https://github.com/RNF-SI/Cicada.git && cd Cicada`
2. **Lancer :** `docker compose up -d`
3. **Attendre** que les migrations s'exécutent (~30 secondes) : `docker compose logs -f web`
4. **Accéder :** http://localhost:8000/admin/ (`admin` / `admin`)

> **Note :** Le fichier `.env` est **optionnel** pour le développement. Les valeurs par défaut permettent de démarrer immédiatement. Pour personnaliser (ports, mots de passe), copiez `.env.example` vers `.env`.

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
- **[Présentation du projet (PDF)](docs/Présentation_projet_CICADA_VF.pdf)** - Présentation générale du projet CICADA
- **[Guide Développeur](docs/GUIDE_DEVELOPPEUR.md)** - Commandes, permissions, logs, i18n, styles
- **[Configuration Email](docs/EMAIL_CONFIGURATION.md)** - Mailpit (dev), SMTP (prod), notifications
- **[Tests](docs/TESTING.md)** - Guide des tests (pytest, Jest)
- **[Release Pipeline](docs/RELEASE_PIPELINE.md)** - Conventional commits, versioning, Docker, deploiement
- **[CLAUDE.md](CLAUDE.md)** - Référence technique pour Claude Code

## Installation en production

Le déploiement se fait via un package Debian (.deb) avec un installeur web intégré.

```bash
# 1. Installer le package
sudo dpkg -i cicada_0.1.15_amd64.deb

# 2. (Optionnel) Préparer une base PostgreSQL externe
sudo cicada-prepare-db

# 3. Ouvrir l'installeur web
# http://votre-serveur:4567
```

**[Guide d'installation complet](docs/INSTALLATION_GUIDE.md)** - Prérequis, configuration Apache/Nginx, base externe, mise à jour

## Technologies

- **Backend** : Django 5.0+, DRF, PostgreSQL 17+ / PostGIS, Redis, Celery
- **Frontend** : Angular 19+, Angular Material, Leaflet
- **Infrastructure** : Docker, package Debian (.deb), systemd

## 🚢 Release et deploiement

Le projet utilise un pipeline automatise : **conventional commits** → **release-please** → **images Docker sur GHCR** → **docker-compose.prod.yml**.

- Les messages de commit suivent la convention [Conventional Commits](https://www.conventionalcommits.org/) (`feat(plans): ...`, `fix(auth): ...`)
- Le versioning et le CHANGELOG sont generes automatiquement par [release-please](https://github.com/googleapis/release-please)
- Chaque release publie des images Docker sur `ghcr.io/rnf-si/cicada-{backend,frontend}`

**[Documentation complete du pipeline de release](docs/RELEASE_PIPELINE.md)**

## 🤝 Contribution

1. Creer une branche depuis `develop`
2. Faire vos modifications en respectant les [conventional commits](docs/RELEASE_PIPELINE.md#1-conventional-commits)
3. Tester localement
4. Creer une Pull Request vers `develop`

## 📄 Licence

Ce projet est sous licence GPL-3.0. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support

- **Issues** : https://github.com/RNF-SI/Cicada/issues
- **Project Board** : https://github.com/RNF-SI/Cicada/projects/1