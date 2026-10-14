# 📚 Documentation CICADA

Index de la documentation pour CICADA - Application web de gestion des plans de gestion d'espaces naturels.

## 📋 Guides API

### API REST - Guides d'utilisation

| Guide | Description | URL |
|-------|-------------|-----|
| **[API Plans de Gestion](API_PLANS_GUIDE.md)** | Guide complet de l'API pour les plans de gestion, fichiers, statistiques | `/api/plans/` |
| **[API Utilisateurs](API_USERS_GUIDE.md)** | Guide de l'API pour la gestion des utilisateurs | `/api/users/` |
| **[API Organismes/Sites](API_ORGANISMES_SITES_GUIDE.md)** | Guide de l'API pour organismes et sites avec GeoJSON | `/api/users/organismes/` |

## 📖 Référentiels et données

| Guide | Description |
|-------|-------------|
| **[Nomenclatures](NOMENCLATURES.md)** | Gestion des nomenclatures et référentiels pour plans de gestion |

### Authentification

Toutes les API utilisent l'authentification JWT :

```bash
# 1. Obtenir un token
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin", "password": "admin"}'

# 2. Utiliser le token
curl -X GET http://localhost:8000/api/plans/plans/ \
  -H "Authorization: Bearer {access_token}"
```

## 🧩 Fonctionnalités

| Document | Description |
|----------|-------------|
| **[Explications fonctionnelles](FONCTIONNALITES.md)** | Logs, notifications, validations, impersonnation, modules, pages d'administration (droits par rôle), tests |

## 🎨 Design System

| Document | Description |
|----------|-------------|
| **[Design System](DESIGN_SYSTEM.md)** | Couleurs, accessibilité WCAG AA, chips, typographie |

## 🛠️ Documentation technique

| Document | Description |
|----------|-------------|
| **[Guide Développeur](GUIDE_DEVELOPPEUR.md)** | Commandes, permissions, logs, i18n, styles |
| **[Design System](DESIGN_SYSTEM.md)** | Palette de couleurs, règles d'accessibilité, composants |
| **[Tests](TESTING.md)** | Guide complet des tests (pytest, Jest) |
| **[Release Pipeline](RELEASE_PIPELINE.md)** | Conventional commits, versioning automatique, Docker, deploiement production |
| **[Configuration Email](EMAIL_CONFIGURATION.md)** | Mailpit (dev), SMTP (prod), templates, Celery |
| **[CLAUDE.md](../CLAUDE.md)** | Référence technique pour Claude Code |
| **[README.md](../README.md)** | Vue d'ensemble et installation rapide |

## 🚀 Déploiement et exploitation

Point d'entrée : **[Infrastructure](INFRASTRUCTURE.md)**, qui situe chaque serveur et renvoie au guide de chacun.

| Document | Description |
|----------|-------------|
| **[Infrastructure](INFRASTRUCTURE.md)** | Qui parle à qui : instance, serveur de bases, dépôt APT, API de suivi, hub, GHCR — schémas, ports, cycle d'une release, vérifications |
| **[Guide d'installation](INSTALLATION_GUIDE.md)** | Installer une instance (paquet Debian, formulaire, base dans Docker ou sur un serveur existant, Apache), la mettre à jour |
| **[Procédure de release](RELEASE_PROCEDURE.md)** | Tag, paquet `.deb`, publication dans le dépôt APT, déploiement, pièges |
| **[Déploiement du hub](DEPLOIEMENT_HUB.md)** | Hub d'exploration fédérée : installation, Apache, enrôlement d'une instance |
| **[API de suivi](../tracking-api/INSTALLATION.md)** | Installer l'API de suivi des instances (serveur de suivi) |
| **[Banc de test en VM](../packaging/vm-bench/README.md)** | Rejouer toute cette infrastructure en local (scénario `a-z`, labo persistant) avant de toucher à la production |
| **[Exploration fédérée en local](MULTI_INSTANCE_LOCAL.md)** | Deux instances de développement + hub sur un poste |

## 🎯 Par cas d'usage

### Pour développeurs frontend

1. **[Design System](DESIGN_SYSTEM.md)** - Couleurs, accessibilité, composants visuels
2. **[API Plans de Gestion](API_PLANS_GUIDE.md)** - Intégration complète des plans
3. **[API Utilisateurs](API_USERS_GUIDE.md)** - Gestion des utilisateurs
4. **[Nomenclatures](NOMENCLATURES.md)** - Référentiels et listes de valeurs
5. **[DEVELOPMENT.md](../DEVELOPMENT.md)** - Architecture et patterns

### Pour administrateurs système

1. **[Infrastructure](INFRASTRUCTURE.md)** - Les serveurs et leurs liens, puis **[Guide d'installation](INSTALLATION_GUIDE.md)** et **[Procédure de release](RELEASE_PROCEDURE.md)**
2. **[Release Pipeline](RELEASE_PIPELINE.md)** - Deploiement production, images Docker, mise a jour
3. **[Explications fonctionnelles](FONCTIONNALITES.md)** - Comprendre les fonctionnalités (logs, validations, etc.)
4. **[Configuration Email](EMAIL_CONFIGURATION.md)** - Configuration SMTP pour l'envoi des notifications
5. **[DEVELOPMENT.md](../DEVELOPMENT.md)** - Installation et déploiement
6. **[Nomenclatures](NOMENCLATURES.md)** - Import et maintenance des référentiels
7. **[CLAUDE.md](../CLAUDE.md)** - Configuration Django et base de données

### Pour gestionnaires d'espaces naturels

1. **[Explications fonctionnelles](FONCTIONNALITES.md)** - Comprendre les notifications, validations, modules
2. **[API Plans de Gestion](API_PLANS_GUIDE.md)** - Utilisation de l'API
3. **[Nomenclatures](NOMENCLATURES.md)** - Consultation des référentiels
4. Interface admin Django : http://localhost:8000/admin/ (`admin` / `admin`)

## 🔗 Liens utiles

- **Projet GitHub** : https://github.com/RNF-SI/Cicada
- **Issues** : https://github.com/RNF-SI/Cicada/issues
- **Admin Django** : http://localhost:8000/admin/
- **API Swagger** : http://localhost:8000/api/schema/swagger/ *(à venir)*

---

**Mise à jour** : Janvier 2025 - Ajout du Design System et des explications fonctionnelles