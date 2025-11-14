# Outil Plan de Gestion

Application web pour la gestion des plans de gestion d'espaces naturels développée pour le CEN (Conservatoire d'Espaces Naturels) et RNF (Réserves Naturelles de France).

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
   - Frontend Angular : http://localhost:4200
   - Backend Django API : http://localhost:8000
   - Interface d'administration : http://localhost:8000/admin

### Commandes Docker utiles

#### Développement

```bash
# Lancer tous les services
docker-compose up

# Lancer en arrière-plan
docker-compose up -d

# Arrêter tous les services
docker-compose down

# Rebuild des images après modifications
docker-compose build

# Voir les logs
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f web
```

#### Gestion de la base de données

```bash
# Accéder au shell Django
docker-compose exec web python manage.py shell

# Exécuter les migrations
docker-compose exec web python manage.py migrate

# Créer un superutilisateur
docker-compose exec web python manage.py createsuperuser

# Accéder à PostgreSQL
docker-compose exec db psql -U outil_user -d outil_plan_gestion
```

#### Services de développement (optionnels)

```bash
# Lancer avec Adminer (interface PostgreSQL) et MailHog
docker-compose --profile dev-tools up

# Adminer sera disponible sur http://localhost:8080
# MailHog sur http://localhost:8025
```

#### Celery (pour V1)

```bash
# Lancer avec Celery
docker-compose --profile celery up

# Ou pour tout lancer
docker-compose --profile full up
```

## 🏗️ Architecture

### Services Docker

- **web** : Application Django backend (port 8000)
- **frontend** : Application Angular en mode développement (port 4200)
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

## 🔧 Développement

Pour plus de détails sur le développement, consultez :
- `CLAUDE.md` - Guide pour Claude Code
- `claude.md` - Spécifications détaillées du projet

### Technologies

- **Backend** : Django 5.0+, Django REST Framework, PostgreSQL, PostGIS, Redis
- **Frontend** : Angular 19+, TypeScript 5+, Angular Material, Leaflet
- **Infrastructure** : Docker

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