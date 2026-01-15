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

## 🛠️ Documentation technique

| Document | Description |
|----------|-------------|
| **[Guide Développeur](GUIDE_DEVELOPPEUR.md)** | Commandes, permissions, logs, i18n, styles |
| **[Tests](TESTING.md)** | Guide complet des tests (pytest, Jest) |
| **[CLAUDE.md](../CLAUDE.md)** | Référence technique pour Claude Code |
| **[README.md](../README.md)** | Vue d'ensemble et installation rapide |

## 🎯 Par cas d'usage

### Pour développeurs frontend

1. **[API Plans de Gestion](API_PLANS_GUIDE.md)** - Intégration complète des plans
2. **[API Utilisateurs](API_USERS_GUIDE.md)** - Gestion des utilisateurs
3. **[Nomenclatures](NOMENCLATURES.md)** - Référentiels et listes de valeurs
4. **[DEVELOPMENT.md](../DEVELOPMENT.md)** - Architecture et patterns

### Pour administrateurs système

1. **[Explications fonctionnelles](FONCTIONNALITES.md)** - Comprendre les fonctionnalités (logs, validations, etc.)
2. **[DEVELOPMENT.md](../DEVELOPMENT.md)** - Installation et déploiement
3. **[Nomenclatures](NOMENCLATURES.md)** - Import et maintenance des référentiels
4. **[CLAUDE.md](../CLAUDE.md)** - Configuration Django et base de données

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

**Mise à jour** : Janvier 2025 - Ajout des explications fonctionnelles