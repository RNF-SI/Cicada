# 📚 Documentation Outil Plan de Gestion

Index de la documentation pour l'Outil Plan de Gestion - Application web de gestion des plans de gestion d'espaces naturels.

## 📋 Guides API

### API REST - Guides d'utilisation

| Guide | Description | URL |
|-------|-------------|-----|
| **[API Plans de Gestion](API_PLANS_GUIDE.md)** | Guide complet de l'API pour les plans de gestion, fichiers, statistiques | `/api/plans/` |
| **[API Utilisateurs](API_USERS_GUIDE.md)** | Guide de l'API pour la gestion des utilisateurs | `/api/users/` |
| **[API Organismes/Sites](API_ORGANISMES_SITES_GUIDE.md)** | Guide de l'API pour organismes et sites avec GeoJSON | `/api/users/organismes/` |

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

## 🛠️ Documentation technique

| Document | Description |
|----------|-------------|
| **[DEVELOPMENT.md](../DEVELOPMENT.md)** | Guide technique complet pour développeurs |
| **[CLAUDE.md](../CLAUDE.md)** | Guide pour Claude Code avec commandes rapides |
| **[claude.md](../claude.md)** | Spécifications métier détaillées du projet |
| **[README.md](../README.md)** | Vue d'ensemble et installation rapide |

## 🎯 Par cas d'usage

### Pour développeurs frontend

1. **[API Plans de Gestion](API_PLANS_GUIDE.md)** - Intégration complète des plans
2. **[API Utilisateurs](API_USERS_GUIDE.md)** - Gestion des utilisateurs
3. **[DEVELOPMENT.md](../DEVELOPMENT.md)** - Architecture et patterns

### Pour administrateurs système

1. **[DEVELOPMENT.md](../DEVELOPMENT.md)** - Installation et déploiement
2. **[CLAUDE.md](../CLAUDE.md)** - Configuration Django et base de données

### Pour gestionnaires d'espaces naturels

1. **[API Plans de Gestion](API_PLANS_GUIDE.md)** - Utilisation de l'API
2. Interface admin Django : http://localhost:8000/admin/ (`admin` / `admin`)

## 🔗 Liens utiles

- **Projet GitHub** : https://github.com/RNF-SI/outil_plan_de_gestion
- **Issues** : https://github.com/RNF-SI/outil_plan_de_gestion/issues
- **Admin Django** : http://localhost:8000/admin/
- **API Swagger** : http://localhost:8000/api/schema/swagger/ *(à venir)*

---

**Mise à jour** : Novembre 2024 - API Plans de Gestion complètement opérationnelle