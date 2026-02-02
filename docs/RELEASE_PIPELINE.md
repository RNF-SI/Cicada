# Pipeline de release

Ce document explique le pipeline de release de CICADA : convention de commits, versioning automatique, build d'images Docker et deploiement en production.

## Vue d'ensemble

```
commit (conventional) ──> PR vers develop ──> commitlint CI ✓
                                                │
                                          merge develop → main
                                                │
                                     release-please cree une PR
                                     (CHANGELOG, version.txt, package.json)
                                                │
                                          merge de la PR
                                                │
                                        GitHub Release v0.X.0
                                                │
                                       docker-publish.yml
                                        ├─ cicada-backend:0.X.0
                                        └─ cicada-frontend:0.X.0
                                                │
                                      serveur de production
                                      CICADA_VERSION=0.X.0
                                      docker compose -f docker-compose.prod.yml up -d
```

## 1. Conventional Commits

Tous les messages de commit doivent suivre la convention [Conventional Commits](https://www.conventionalcommits.org/).

### Format

```
<type>(<scope>): <description>

[corps optionnel]

[footer(s) optionnel(s)]
```

### Types autorises

| Type | Usage |
|------|-------|
| `feat` | Nouvelle fonctionnalite |
| `fix` | Correction de bug |
| `docs` | Documentation uniquement |
| `style` | Formatage, pas de changement de logique |
| `refactor` | Refactoring sans ajout de fonctionnalite |
| `perf` | Amelioration de performance |
| `test` | Ajout ou modification de tests |
| `build` | Systeme de build, dependances |
| `ci` | Configuration CI/CD |
| `chore` | Maintenance |
| `revert` | Revert d'un commit precedent |

### Scopes du projet

`auth`, `users`, `plans`, `sites`, `organismes`, `notifications`, `activity`, `core`, `api`, `frontend`, `backend`, `docker`, `deps`, `styles`, `tests`, `i18n`, `release`

### Exemples

```bash
# Fonctionnalite
feat(plans): ajouter l'export PDF des plans de gestion

# Correction
fix(auth): corriger le refresh token qui expirait trop tot

# Plusieurs lignes
feat(sites): import en masse depuis GeoJSON

Permet d'importer jusqu'a 500 sites en une seule operation.
Les doublons INPN sont detectes automatiquement.

Closes #42
```

### Enforcement

Le linting est fait **en CI uniquement** (pas de hooks locaux). Le workflow `.github/workflows/commitlint.yml` valide les messages de commit sur chaque PR vers `main` ou `develop`. Si un message ne respecte pas la convention, la PR est bloquee.

Configuration : `commitlint.config.js` a la racine du projet.

> **Pourquoi pas de hooks locaux ?** Les hooks via husky necessitent `npm install` a la racine, ce qui ajoute de la friction pour les developpeurs backend-only. Le CI suffit pour bloquer les PRs non conformes.

## 2. Versioning automatique avec release-please

[release-please](https://github.com/googleapis/release-please) analyse les commits sur `main` et cree automatiquement une PR de release avec :

- Mise a jour du `CHANGELOG.md`
- Mise a jour de `version.txt` (source de verite)
- Mise a jour de `frontend/package.json`

### Fonctionnement

1. Les commits `feat` incrementent la version **mineure** (0.1.0 → 0.2.0)
2. Les commits `fix` incrementent le **patch** (0.1.0 → 0.1.1)
3. Un commit avec `BREAKING CHANGE` dans le footer incremente la version **majeure** (0.1.0 → 1.0.0)

Quand la PR de release est mergee, release-please cree automatiquement un **tag Git** et une **GitHub Release**.

> **Important** : release-please utilise un Personal Access Token (`RELEASE_PAT`) au lieu du `GITHUB_TOKEN` par defaut. C'est necessaire car les tags crees par `GITHUB_TOKEN` ne declenchent pas les autres workflows (protection anti-boucle de GitHub). Le secret `RELEASE_PAT` doit etre configure dans **Settings > Secrets > Actions** du repo avec les permissions `contents: write` et `pull-requests: write`.

### Fichiers de configuration

| Fichier | Role |
|---------|------|
| `version.txt` | Source de verite de la version courante |
| `release-please-config.json` | Configuration (type `simple`, fichiers a mettre a jour) |
| `.release-please-manifest.json` | Version actuelle pour release-please |

### Pourquoi `release-type: simple` ?

Le backend et le frontend sont **tightly coupled** et partagent la meme version. Un `version.txt` est plus neutre qu'un `package.json` ou `setup.py` comme source de verite.

## 3. Images Docker de production

Chaque release publiee declenche le workflow `.github/workflows/docker-publish.yml` qui build et push deux images sur **GitHub Container Registry (GHCR)** :

- `ghcr.io/rnf-si/cicada-backend:<version>`
- `ghcr.io/rnf-si/cicada-frontend:<version>`

Les images sont aussi taguees `:latest`.

### Differences entre les Dockerfiles dev et prod

| | Dev (`backend/Dockerfile`) | Prod (`backend/Dockerfile.prod`) |
|---|---|---|
| Serveur | `runserver` (Django) | `gunicorn` (3 workers) |
| Settings | `config.settings.development` | `config.settings.production` |
| User | root | `cicada` (non-root) |
| Deps systeme | `build-essential` inclus | Pas de compilateur |
| Volumes | Code monte en volume | Code copie dans l'image |

Le frontend utilise le meme `Dockerfile` pour dev et prod (build multi-stage avec Apache).

### Build local pour tester

```bash
# Backend
cd backend
docker build -f Dockerfile.prod -t cicada-backend:test .

# Frontend
cd frontend
docker build -t cicada-frontend:test .
```

## 4. Deploiement en production

### Configuration

1. Copier le template d'environnement :
   ```bash
   cp .env.prod.example .env
   ```

2. Remplir **toutes** les variables requises dans `.env` :

   | Variable | Description |
   |----------|-------------|
   | `CICADA_VERSION` | Version a deployer (ex: `0.2.0`) ou `latest` |
   | `SECRET_KEY` | Cle secrete Django (generee aleatoirement) |
   | `ALLOWED_HOSTS` | Nom(s) de domaine du serveur |
   | `POSTGRES_DB` | Nom de la base de donnees |
   | `POSTGRES_USER` | Utilisateur PostgreSQL |
   | `POSTGRES_PASSWORD` | Mot de passe PostgreSQL |
   | `REDIS_PASSWORD` | Mot de passe Redis |

   Variables optionnelles : `CORS_ALLOWED_ORIGINS`, `EMAIL_HOST`, `EMAIL_PORT`, `FRONTEND_PORT`, etc.

3. Lancer les services :
   ```bash
   docker compose -f docker-compose.prod.yml up -d
   ```

### Services production

Le fichier `docker-compose.prod.yml` contient 6 services :

| Service | Image | Role |
|---------|-------|------|
| `db` | `postgis/postgis:17-3.5-alpine` | Base de donnees |
| `redis` | `redis:7-alpine` | Cache et broker Celery |
| `web` | `ghcr.io/rnf-si/cicada-backend` | API Django (gunicorn) |
| `frontend` | `ghcr.io/rnf-si/cicada-frontend` | SPA Angular (Apache) |
| `celery-worker` | `ghcr.io/rnf-si/cicada-backend` | Taches asynchrones |
| `celery-beat` | `ghcr.io/rnf-si/cicada-backend` | Taches planifiees |

### Mise a jour vers une nouvelle version

```bash
# Mettre a jour la version dans .env
# CICADA_VERSION=0.3.0

# Tirer les nouvelles images et redemarrer
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Generer une SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Verifications post-deploiement

```bash
# API health check
curl http://localhost/api/health/

# Page d'accueil frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost/

# Logs
docker compose -f docker-compose.prod.yml logs -f web
```

## 5. Architecture des workflows CI/CD

```
.github/workflows/
├── tests.yml             # Tests backend + frontend (push/PR)
├── commitlint.yml        # Validation des messages de commit (PR)
├── release-please.yml    # Versioning automatique (push main)
└── docker-publish.yml    # Build & push Docker (release published)
```

| Workflow | Declencheur | Action |
|----------|-------------|--------|
| `tests.yml` | Push / PR vers main, develop | Lance pytest et jest |
| `commitlint.yml` | PR vers main, develop | Valide les messages de commit |
| `release-please.yml` | Push vers main | Cree/met a jour une PR de release |
| `docker-publish.yml` | Push d'un tag `v*` | Build et push des images GHCR |
