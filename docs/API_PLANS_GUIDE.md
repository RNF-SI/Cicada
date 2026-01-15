# 📋 API REST Plans de Gestion - Guide d'utilisation

Guide complet de l'API REST pour la gestion des Plans de Gestion des espaces naturels.

## 🔗 Endpoints disponibles

### Plans de Gestion

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/plans/plans/` | Liste paginée des plans |
| POST | `/api/plans/plans/` | Créer un nouveau plan |
| GET | `/api/plans/plans/{id}/` | Détail d'un plan spécifique |
| PATCH | `/api/plans/plans/{id}/` | Modifier un plan |
| DELETE | `/api/plans/plans/{id}/` | Supprimer un plan |

### Actions spéciales sur les plans

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/plans/plans/geojson_list/` | Liste des plans au format GeoJSON |
| GET | `/api/plans/plans/{id}/geojson/` | Plan individuel au format GeoJSON |
| GET | `/api/plans/plans/stats/` | Statistiques des plans |
| POST | `/api/plans/plans/{id}/assign_site/` | Assigner un site à un plan |
| DELETE | `/api/plans/plans/{id}/remove_site/` | Retirer un site d'un plan |
| POST | `/api/plans/plans/{id}/assign_referent/` | Assigner un référent |
| DELETE | `/api/plans/plans/{id}/remove_referent/` | Retirer un référent |

### Fichiers de plans

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/plans/fichiers/` | Liste des fichiers |
| POST | `/api/plans/fichiers/` | Upload d'un fichier |
| GET | `/api/plans/fichiers/{id}/` | Détail d'un fichier |
| PATCH | `/api/plans/fichiers/{id}/` | Modifier les métadonnées |
| DELETE | `/api/plans/fichiers/{id}/` | Supprimer un fichier |
| GET | `/api/plans/fichiers/{id}/download/` | Télécharger un fichier |

### Actions en masse

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/plans/bulk_assign_sites/` | Assigner plusieurs sites à plusieurs plans |
| GET | `/api/plans/export_geojson/` | Export GeoJSON complet |

## 🔑 Authentification

L'API utilise l'authentification JWT. Vous devez d'abord obtenir un token d'accès :

```bash
# 1. Obtenir un token
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin", "password": "admin"}'

# Réponse
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {...}
}

# 2. Utiliser le token dans les requêtes
curl -X GET http://localhost:8000/api/plans/plans/ \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
```

## 📋 Utilisation de l'API

### 1. Liste des plans de gestion

**GET /api/plans/plans/**

```bash
curl -X GET http://localhost:8000/api/plans/plans/ \
  -H "Authorization: Bearer {token}"
```

**Réponse :**
```json
{
  "count": 4,
  "next": null,
  "previous": null,
  "current_page": 1,
  "total_pages": 1,
  "page_size": 20,
  "results": [
    {
      "id_pg": 1,
      "nom": "Plan de gestion 2020-2030 - Réserve Naturelle de Camargue",
      "id_cdr": 2020001,
      "annee_debut": 2020,
      "annee_fin": 2030,
      "periode_gestion": "2020-2030",
      "gestion_partagee": false,
      "statut": "valide",
      "statut_display": "Validé",
      "version": "2.0",
      "evaluation_display": "Évaluation finale",
      "redacteur_type_display": "Gestionnaire",
      "redacteur_nom": "SNPN - Réserve de Camargue",
      "nb_sites": 1,
      "nb_fichiers": 3,
      "date_ajout": "2024-11-20T15:47:21.123456Z",
      "date_maj": "2024-11-20T15:47:21.123456Z"
    }
  ]
}
```

### 2. Filtres et recherche

**Filtres disponibles :**

| Paramètre | Type | Description | Exemple |
|-----------|------|-------------|---------|
| `statut` | string | Statut du plan | `statut=valide` |
| `gestion_partagee` | boolean | Plan multi-sites | `gestion_partagee=true` |
| `ct88` | boolean | Circulaire CT88 | `ct88=true` |
| `risque_incendie` | boolean | Risque incendie | `risque_incendie=true` |
| `annee_debut` | integer | Année de début | `annee_debut=2020` |
| `annee_fin` | integer | Année de fin | `annee_fin=2030` |
| `actif_en_annee` | integer | Actif dans l'année | `actif_en_annee=2024` |
| `site_id` | integer | Site associé | `site_id=1` |
| `organisme_id` | integer | Organisme gestionnaire | `organisme_id=1` |
| `referent_id` | integer | Référent assigné | `referent_id=2` |
| `a_geometrie` | boolean | A une géométrie | `a_geometrie=true` |
| `search` | string | Recherche textuelle | `search=Camargue` |

**Exemples :**

```bash
# Plans validés
curl -X GET "http://localhost:8000/api/plans/plans/?statut=valide" \
  -H "Authorization: Bearer {token}"

# Plans actifs en 2024
curl -X GET "http://localhost:8000/api/plans/plans/?actif_en_annee=2024" \
  -H "Authorization: Bearer {token}"

# Recherche par nom
curl -X GET "http://localhost:8000/api/plans/plans/?search=Camargue" \
  -H "Authorization: Bearer {token}"

# Filtres combinés
curl -X GET "http://localhost:8000/api/plans/plans/?statut=valide&gestion_partagee=true&ct88=true" \
  -H "Authorization: Bearer {token}"
```

### 3. Détail d'un plan

**GET /api/plans/plans/{id}/**

```bash
curl -X GET http://localhost:8000/api/plans/plans/1/ \
  -H "Authorization: Bearer {token}"
```

**Réponse :**
```json
{
  "id_pg": 1,
  "nom": "Plan de gestion 2020-2030 - Réserve Naturelle de Camargue",
  "uuid": "a1b2c3d4-e5f6-7g8h-9i0j-k1l2m3n4o5p6",
  "id_cdr": 2020001,
  "annee_debut": 2020,
  "annee_fin": 2030,
  "periode_gestion": "2020-2030",
  "gestion_partagee": false,
  "autres_ep": null,
  "ct88": true,
  "risque_incendie": true,
  "evaluation_display": "Évaluation finale",
  "redacteur_type_display": "Gestionnaire",
  "redacteur_nom": "SNPN - Réserve de Camargue",
  "commentaire": "Plan de gestion quinquennal...",
  "statut": "valide",
  "statut_display": "Validé",
  "version": "2.0",
  "geometrie": null,
  "is_multi_sites": false,
  "organismes_gestionnaires": ["RNF"],
  "sites_list": [
    {
      "id_site": 1,
      "nom_site": "Réserve Naturelle de la Camargue"
    }
  ],
  "sites": [
    {
      "id_cor_site_pg": 1,
      "site": {
        "id_site": 1,
        "nom_site": "Réserve Naturelle de la Camargue",
        "surf_off": 13117.0,
        "active": true
      },
      "rang": 1,
      "commentaire": "Site principal du plan",
      "date_ajout": "2024-11-20T15:47:21Z",
      "date_maj": "2024-11-20T15:47:21Z"
    }
  ],
  "fichiers": [
    {
      "id_fichier": 1,
      "nom_fichier": "Plan_Camargue_2020-2030_Document_Principal.pdf",
      "url": "/media/plans/1/Plan_Camargue_2020-2030_Document_Principal.pdf",
      "type_fichier": "document",
      "titre": "Document principal du plan de gestion",
      "description": "Document principal contenant l'ensemble du plan",
      "auteur": "SNPN",
      "public": true,
      "ordre_affichage": 1,
      "taille_fichier": 1524000,
      "file_size_human": "1.5 MB",
      "is_image": false,
      "is_document": true,
      "date_upload": "2024-11-20T15:47:21Z"
    }
  ],
  "referents": [
    {
      "id_role": 2,
      "email": "marie.dupont@rnf.fr",
      "nom_complet": "Marie Dupont",
      "role_level": "referent"
    }
  ],
  "utilisateur_ajout": {
    "id_role": 1,
    "email": "admin",
    "nom_complet": "admin",
    "role_level": "super_admin"
  },
  "utilisateur_maj": {
    "id_role": 2,
    "email": "marie.dupont@rnf.fr", 
    "nom_complet": "Marie Dupont",
    "role_level": "referent"
  },
  "date_ajout": "2024-11-20T15:47:21Z",
  "date_maj": "2024-11-20T15:47:21Z"
}
```

### 4. Création d'un plan

**POST /api/plans/plans/**

```bash
curl -X POST http://localhost:8000/api/plans/plans/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "nom": "Nouveau Plan de Gestion 2025-2035",
    "id_cdr": 2025001,
    "annee_debut": 2025,
    "annee_fin": 2035,
    "gestion_partagee": false,
    "ct88": false,
    "risque_incendie": false,
    "id_evaluation": 1,
    "id_redacteur_type": 1,
    "redacteur_nom": "Exemple Organisme",
    "commentaire": "Plan créé via API",
    "statut": "draft",
    "version": "1.0",
    "sites_ids": [1, 2],
    "referents_ids": [2]
  }'
```

### 5. Modification d'un plan

**PATCH /api/plans/plans/{id}/**

```bash
curl -X PATCH http://localhost:8000/api/plans/plans/1/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "commentaire": "Plan modifié via API",
    "statut": "valide",
    "referents_ids": [2, 3]
  }'
```

### 6. Format GeoJSON

**GET /api/plans/plans/geojson_list/**

```bash
curl -X GET http://localhost:8000/api/plans/plans/geojson_list/ \
  -H "Authorization: Bearer {token}"
```

**Réponse :**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "MultiPolygon",
        "coordinates": [...]
      },
      "properties": {
        "id_pg": 1,
        "nom": "Plan de gestion 2020-2030 - Réserve Naturelle de Camargue",
        "periode_gestion": "2020-2030",
        "gestion_partagee": false,
        "statut": "valide",
        "statut_display": "Validé",
        "nb_sites": 1
      }
    }
  ]
}
```

### 7. Statistiques

**GET /api/plans/plans/stats/**

```bash
curl -X GET http://localhost:8000/api/plans/plans/stats/ \
  -H "Authorization: Bearer {token}"
```

**Réponse :**
```json
{
  "total": 4,
  "par_statut": {
    "draft": 2,
    "valide": 1,
    "archive": 1
  },
  "par_periode": {
    "2024": 2,
    "2025": 3,
    "2026": 2
  },
  "gestion_partagee": 1,
  "avec_geometrie": 0,
  "ct88": 2,
  "risque_incendie": 1
}
```

### 8. Assignation de sites

**POST /api/plans/plans/{id}/assign_site/**

```bash
curl -X POST http://localhost:8000/api/plans/plans/1/assign_site/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "site_id": 2,
    "rang": 2,
    "commentaire": "Site secondaire"
  }'
```

### 9. Gestion des fichiers

**Upload d'un fichier :**

```bash
curl -X POST http://localhost:8000/api/plans/fichiers/ \
  -H "Authorization: Bearer {token}" \
  -F "fichier=@document.pdf" \
  -F "plan_de_gestion=1" \
  -F "type_fichier=document" \
  -F "titre=Document test" \
  -F "description=Fichier uploadé via API" \
  -F "auteur=API User" \
  -F "public=true" \
  -F "ordre_affichage=1"
```

**Téléchargement d'un fichier :**

```bash
curl -X GET http://localhost:8000/api/plans/fichiers/1/download/ \
  -H "Authorization: Bearer {token}" \
  --output document.pdf
```

### 10. Actions en masse

**Assignation multiple :**

```bash
curl -X POST http://localhost:8000/api/plans/bulk_assign_sites/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_ids": [1, 2, 3],
    "site_ids": [4, 5],
    "commentaire": "Assignation en masse via API"
  }'
```

## 🔐 Permissions

| Rôle | Permissions |
|------|-------------|
| **Super Admin** | Accès total à tous les plans |
| **Admin Organisme** | Plans des sites de son organisme |
| **Référent** | Plans des sites assignés + plans dont il est référent |
| **Utilisateur** | Plans publics validés uniquement |

## ⚠️ Gestion d'erreurs

### Erreurs d'authentification

```json
// 401 - Token manquant
{"detail": "Authentication credentials were not provided."}

// 401 - Token invalide
{"detail": "Given token not valid for any token type"}
```

### Erreurs de permissions

```json
// 403 - Permissions insuffisantes
{"detail": "You do not have permission to perform this action."}
```

### Erreurs de validation

```json
// 400 - Données invalides
{
  "nom": ["Ce champ est obligatoire."],
  "annee_debut": ["Assurez-vous que cette valeur est supérieure ou égale à 1900."]
}
```

### Erreurs de ressource

```json
// 404 - Plan non trouvé
{"detail": "Not found."}
```

## 📊 Pagination

La pagination utilise le format standard de Django REST Framework :

```json
{
  "count": 50,
  "next": "http://localhost:8000/api/plans/plans/?page=3",
  "previous": "http://localhost:8000/api/plans/plans/?page=1", 
  "current_page": 2,
  "total_pages": 3,
  "page_size": 20,
  "results": [...]
}
```

**Paramètres de pagination :**
- `page` : Numéro de page (défaut: 1)
- `page_size` : Nombre d'éléments par page (défaut: 20, max: 100)

## 🎯 Bonnes pratiques

1. **Utilisez toujours HTTPS** en production
2. **Gérez l'expiration des tokens** (renouvellement automatique)
3. **Filtrez les données** plutôt que de récupérer toute la liste
4. **Utilisez la pagination** pour les grandes listes
5. **Vérifiez les permissions** avant les opérations sensibles
6. **Gérez les erreurs** avec des try/catch appropriés
7. **Loggez les actions importantes** côté client

## 📝 Exemples d'intégration

### JavaScript/Fetch

```javascript
class PlanGestionAPI {
  constructor(baseURL, token) {
    this.baseURL = baseURL;
    this.token = token;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    };

    const response = await fetch(url, config);
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }
    
    return response.json();
  }

  // Lister les plans
  async getPlans(filters = {}) {
    const params = new URLSearchParams(filters);
    return this.request(`/api/plans/plans/?${params}`);
  }

  // Créer un plan
  async createPlan(planData) {
    return this.request('/api/plans/plans/', {
      method: 'POST',
      body: JSON.stringify(planData)
    });
  }

  // Statistiques
  async getStats() {
    return this.request('/api/plans/plans/stats/');
  }
}

// Usage
const api = new PlanGestionAPI('http://localhost:8000', 'your-jwt-token');
const plans = await api.getPlans({ statut: 'valide' });
```

### Python/Requests

```python
import requests

class PlanGestionAPI:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def get_plans(self, **filters):
        response = requests.get(
            f'{self.base_url}/api/plans/plans/',
            headers=self.headers,
            params=filters
        )
        response.raise_for_status()
        return response.json()
    
    def create_plan(self, plan_data):
        response = requests.post(
            f'{self.base_url}/api/plans/plans/',
            headers=self.headers,
            json=plan_data
        )
        response.raise_for_status()
        return response.json()

# Usage
api = PlanGestionAPI('http://localhost:8000', 'your-jwt-token')
plans = api.get_plans(statut='valide')
```

---

Cette API REST est maintenant complètement fonctionnelle et prête pour l'intégration avec le frontend Angular ! 🚀