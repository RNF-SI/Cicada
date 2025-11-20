# 📖 Guide API REST Organismes et Sites

## 🔗 Endpoints disponibles

### **Authentification requise**
Tous les endpoints nécessitent un token JWT dans l'en-tête :
```bash
Authorization: Bearer {access_token}
```

---

## 🏢 **Gestion des organismes**

### **GET /api/users/organismes/**
Liste paginée des organismes avec filtres.

**Permissions :** Authentifié (filtrage automatique selon rôle)

**Paramètres de requête :**
- `page` : Numéro de page (défaut: 1)
- `page_size` : Taille de page (défaut: 20, max: 100)
- `search` : Recherche globale (nom, ville, email, adresse)
- `nom` : Nom organisme (contient)
- `ville` : Ville (contient)
- `active` : true/false
- `is_parent` : Organisme parent (true/false)
- `has_sites` : Gère des sites (true/false)
- `ordering` : Tri (nom, ville, id)

**Exemple :**
```bash
GET /api/users/organismes/?search=RNF&active=true&page_size=10
```

**Réponse :**
```json
{
  "links": {
    "next": "http://localhost:8000/api/users/organismes/?page=2",
    "previous": null
  },
  "pagination": {
    "count": 15,
    "current_page": 1,
    "total_pages": 2,
    "page_size": 10
  },
  "results": [
    {
      "id_organisme": 1,
      "nom_organisme": "Réserves Naturelles de France",
      "ville_organisme": "Dijon",
      "email_organisme": "contact@rnf.fr",
      "url_organisme": "https://www.reserves-naturelles.org",
      "parent_organisme": null,
      "sites_count": 12,
      "users_count": 8,
      "active": true
    }
  ]
}
```

---

### **GET /api/users/organismes/{id}/**
Détail complet d'un organisme.

**Permissions :** Voir l'organisme selon son rôle

**Réponse :**
```json
{
  "id_organisme": 1,
  "nom_organisme": "Réserves Naturelles de France",
  "adresse_organisme": "1 rue de la Nature",
  "ville_organisme": "Dijon",
  "email_organisme": "contact@rnf.fr",
  "parent_organisme": null,
  "enfants_organismes": [
    {
      "id_organisme": 2,
      "nom_organisme": "CEN Auvergne-Rhône-Alpes"
    }
  ],
  "sites_geres": [
    {
      "site": {
        "id_site": 1,
        "nom_site": "Réserve Naturelle de la Camargue",
        "surf_off": 13117.0,
        "active": true
      }
    }
  ],
  "users": [
    {
      "id_role": 2,
      "nom_complet": "Marie Dupont",
      "email": "marie.dupont@rnf.fr",
      "role_level": "utilisateur"
    }
  ],
  "statistiques": {
    "total_users": 8,
    "active_users": 7,
    "total_sites": 12
  }
}
```

---

### **POST /api/users/organismes/**
Créer un organisme.

**Permissions :** Admin Organisme+

**Payload :**
```json
{
  "nom_organisme": "Nouveau CEN",
  "ville_organisme": "Lyon",
  "email_organisme": "contact@nouveau-cen.fr",
  "adresse_organisme": "123 rue de l'Environnement",
  "cp_organisme": "69000",
  "tel_organisme": "04 XX XX XX XX",
  "url_organisme": "https://www.nouveau-cen.fr",
  "parent_id": 1,
  "active": true
}
```

**Validations métier :**
- Nom organisme requis (min 3 caractères)
- Admin organisme ne peut créer que des enfants de son organisme

---

### **PATCH /api/users/organismes/{id}/**
Modifier un organisme.

**Permissions :** Admin de l'organisme OU Super Admin

**Payload :**
```json
{
  "email_organisme": "nouveau-contact@cen.fr",
  "tel_organisme": "04 YY YY YY YY"
}
```

---

## 🏛️  **Gestion des sites**

### **GET /api/users/sites/**
Liste paginée des sites avec filtres.

**Permissions :** Authentifié (filtrage automatique selon rôle)

**Paramètres de requête :**
- `search` : Recherche globale (nom, id_local, id_inpn)
- `nom` : Nom site (contient)
- `type_site` : ID type de site
- `surf_min` / `surf_max` : Surface min/max en hectares
- `active` : true/false
- `marin` : Milieu marin (true/false)
- `has_geometry` : A une géométrie (true/false)
- `organisme` : ID organisme gestionnaire
- `has_referent` : A un référent validé (true/false)
- `ordering` : Tri (nom, surface, date_creation)

**Exemple :**
```bash
GET /api/users/sites/?surf_min=1000&marin=false&ordering=nom
```

**Réponse :**
```json
{
  "pagination": {...},
  "results": [
    {
      "id_site": 1,
      "nom_site": "Réserve Naturelle de la Camargue",
      "id_local": "RNN01",
      "surf_off": 13117.0,
      "type_site": "Réserve Naturelle Nationale",
      "date_crea": "1975-04-03",
      "marin": false,
      "active": true,
      "geom_pt_geojson": {
        "type": "Point",
        "coordinates": [4.6483, 43.5527]
      },
      "organismes_count": 2,
      "users_count": 3
    }
  ]
}
```

---

### **GET /api/users/sites/{id}/**
Détail complet d'un site.

**Permissions :** Voir le site selon son rôle

**Réponse :**
```json
{
  "id_site": 1,
  "nom_site": "Réserve Naturelle de la Camargue",
  "surf_off": 13117.0,
  "type_site": {
    "id_nomenclature": 1,
    "label_default": "Réserve Naturelle Nationale",
    "cd_nomenclature": "RNN"
  },
  "geom_wkt": "MULTIPOLYGON(...)",
  "geom_pt_wkt": "POINT(4.6483 43.5527)",
  "organismes_gestionnaires": [
    {
      "organisme": {
        "id_organisme": 1,
        "nom_organisme": "RNF",
        "email_organisme": "contact@rnf.fr"
      }
    }
  ],
  "users_assignes": [
    {
      "user": {
        "id_role": 2,
        "nom_complet": "Marie Dupont",
        "email": "marie.dupont@rnf.fr",
        "role_level": "referent"
      },
      "referent": true,
      "referent_valid": true,
      "conservateur": false
    }
  ]
}
```

---

### **GET /api/users/sites/{id}/geojson/**
Site au format GeoJSON complet.

**Permissions :** Voir le site selon son rôle

**Réponse :**
```json
{
  "type": "Feature",
  "id": 1,
  "geometry": {
    "type": "MultiPolygon",
    "coordinates": [[[...]]]
  },
  "properties": {
    "id_site": 1,
    "nom_site": "Réserve Naturelle de la Camargue",
    "surf_off": 13117.0,
    "type_site": "Réserve Naturelle Nationale",
    "organismes_gestionnaires": [...],
    "users_assignes": [...]
  }
}
```

---

### **GET /api/users/sites/geojson_list/**
Liste des sites au format FeatureCollection GeoJSON.

**Permissions :** Authentifié (filtrage selon rôle)

**Paramètres :** Accepte les mêmes filtres que la liste normale

**Réponse :**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": 1,
      "geometry": {...},
      "properties": {...}
    }
  ],
  "properties": {
    "count": 15,
    "note": "Limité à 100 sites pour les performances"
  }
}
```

---

### **POST /api/users/sites/**
Créer un site.

**Permissions :** Admin Organisme+

**Payload :**
```json
{
  "nom_site": "Nouveau Site Naturel",
  "id_local": "NS001",
  "surf_off": 456.78,
  "type_site_id": 1,
  "date_crea": "2024-01-15",
  "marin": false,
  "active": true,
  "geom_pt_geojson": {
    "type": "Point",
    "coordinates": [2.3522, 48.8566]
  }
}
```

**Support géospatial :**
- `geom_geojson` : Géométrie principale (Polygon/MultiPolygon)
- `geom_pt_geojson` : Point de référence

---

### **POST /api/users/sites/**
Créer un site avec géométrie complète.

**Exemple avec géométrie :**
```json
{
  "nom_site": "Site avec Géométrie",
  "surf_off": 123.45,
  "geom_geojson": {
    "type": "Polygon",
    "coordinates": [[[
      [2.35, 48.85],
      [2.36, 48.85],
      [2.36, 48.86],
      [2.35, 48.86],
      [2.35, 48.85]
    ]]]
  },
  "geom_pt_geojson": {
    "type": "Point",
    "coordinates": [2.355, 48.855]
  }
}
```

---

## 🔗 **Relations et assignations**

### **POST /api/users/organismes/{id}/assign_site/**
Assigner un site à un organisme.

**Permissions :** Admin Organisme+ (peut gérer le site)

**Payload :**
```json
{
  "site_id": 1
}
```

---

### **POST /api/users/organismes/{id}/bulk_assign_sites/**
Assignation en masse de sites à un organisme.

**Permissions :** Admin Organisme+ (peut gérer les sites)

**Payload :**
```json
{
  "site_ids": [1, 2, 3, 4]
}
```

**Réponse :**
```json
{
  "assigned": [
    {"id_site": 1, "nom_site": "Site A"}
  ],
  "already_assigned": [
    {"id_site": 2, "nom_site": "Site B"}
  ],
  "forbidden": [
    {"id_site": 3, "nom_site": "Site C"}
  ]
}
```

---

### **DELETE /api/users/organismes/{organisme_pk}/sites/{site_pk}/**
Désassigner un site d'un organisme.

**Permissions :** Admin Organisme+ (peut gérer le site)

---

### **POST /api/users/sites/{id}/assign_user/**
Assigner un utilisateur au site.

**Permissions :** Admin Organisme+ (peut gérer le site)

**Payload :**
```json
{
  "user_id": 2,
  "referent": true,
  "referent_valid": true,
  "conservateur": false
}
```

---

### **DELETE /api/users/sites/{site_pk}/users/{user_pk}/**
Désassigner un utilisateur du site.

**Permissions :** Admin Organisme+ (peut gérer le site)

---

## 📊 **Actions spécialisées**

### **GET /api/users/organismes/{id}/sites/**
Liste des sites gérés par un organisme.

**Permissions :** Voir l'organisme selon son rôle

**Réponse :**
```json
[
  {
    "id_site": 1,
    "nom_site": "Réserve de la Camargue",
    "surf_off": 13117.0,
    "type_site": "RNN",
    "active": true
  }
]
```

---

### **GET /api/users/sites/{id}/users/**
Liste des utilisateurs assignés au site.

**Réponse :**
```json
[
  {
    "id_role": 2,
    "nom_complet": "Marie Dupont",
    "email": "marie.dupont@rnf.fr",
    "role_level": "referent",
    "referent": true,
    "referent_valid": true,
    "conservateur": false
  }
]
```

---

### **GET /api/users/sites/{id}/organismes/**
Liste des organismes gestionnaires du site.

**Réponse :**
```json
[
  {
    "id_organisme": 1,
    "nom_organisme": "RNF",
    "ville_organisme": "Dijon",
    "email_organisme": "contact@rnf.fr"
  }
]
```

---

### **GET /api/users/organismes/stats/**
Statistiques des organismes.

**Permissions :** Admin Organisme+

**Réponse :**
```json
{
  "total_organismes": 15,
  "active_organismes": 14,
  "organismes_parents": 3,
  "organismes_enfants": 12
}
```

---

### **GET /api/users/sites/stats/**
Statistiques des sites.

**Permissions :** Référent+

**Réponse :**
```json
{
  "total_sites": 45,
  "active_sites": 42,
  "sites_marins": 12,
  "sites_outre_mer": 8,
  "surface_totale_ha": 125634.78
}
```

---

## 🔍 **Filtres avancés**

### **Filtres organismes**
- `search` : Recherche dans nom, ville, email, adresse
- `nom` / `nom_exact` : Nom organisme
- `ville` / `cp` : Ville et code postal
- `has_email` / `has_phone` / `has_website` : A email/téléphone/site web
- `is_parent` / `has_parent` : Structure hiérarchique
- `parent_id` : ID organisme parent
- `has_sites` / `has_users` : A des sites/utilisateurs

### **Filtres sites**
- `search` : Recherche dans nom, id_local, id_inpn
- `type_site` / `type_site_label` : Type de site
- `surf_min` / `surf_max` / `surf_range` : Surface
- `created_after` / `created_before` / `created_year` : Dates
- `has_geometry` / `has_point` : Géométries
- `organisme` / `organisme_nom` : Organisme gestionnaire
- `user` / `user_email` : Utilisateur assigné
- `has_referent` : A un référent validé

---

## 🗺️ **Support GeoJSON**

### **Formats supportés**

**Import (création/modification) :**
```json
{
  "geom_geojson": {
    "type": "Polygon|MultiPolygon",
    "coordinates": [...]
  },
  "geom_pt_geojson": {
    "type": "Point",
    "coordinates": [longitude, latitude]
  }
}
```

**Export (lecture) :**
- `/sites/{id}/geojson/` : Site complet en Feature GeoJSON
- `/sites/geojson_list/` : Tous les sites en FeatureCollection
- Géométries automatiquement converties de PostGIS vers GeoJSON

### **Projections**
- **Stockage** : EPSG:4326 (WGS84) dans PostGIS
- **API** : Coordonnées en longitude/latitude (EPSG:4326)
- **Frontend** : Affichage Lambert-93 (EPSG:2154) recommandé

---

## ⚡ **Exemples d'utilisation**

### **Obtenir token et lister organismes**
```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin", "password": "admin"}' \
  | jq -r '.access')

# 2. Lister organismes
curl -X GET http://localhost:8000/api/users/organismes/ \
  -H "Authorization: Bearer $TOKEN"
```

### **Créer un organisme**
```bash
curl -X POST http://localhost:8000/api/users/organismes/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nom_organisme": "Nouveau CEN",
    "ville_organisme": "Lyon",
    "email_organisme": "contact@nouveau-cen.fr",
    "active": true
  }'
```

### **Créer un site avec géométrie**
```bash
curl -X POST http://localhost:8000/api/users/sites/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nom_site": "Site Test GeoJSON",
    "surf_off": 100.5,
    "geom_pt_geojson": {
      "type": "Point",
      "coordinates": [2.3522, 48.8566]
    },
    "active": true
  }'
```

### **Obtenir sites au format GeoJSON**
```bash
# Tous les sites en FeatureCollection
curl -X GET http://localhost:8000/api/users/sites/geojson_list/ \
  -H "Authorization: Bearer $TOKEN"

# Site spécifique en Feature
curl -X GET http://localhost:8000/api/users/sites/1/geojson/ \
  -H "Authorization: Bearer $TOKEN"
```

### **Assigner sites à un organisme en masse**
```bash
curl -X POST http://localhost:8000/api/users/organismes/1/bulk_assign_sites/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "site_ids": [1, 2, 3]
  }'
```

### **Filtrer et rechercher**
```bash
# Sites marins > 1000 ha
curl -X GET "http://localhost:8000/api/users/sites/?marin=true&surf_min=1000" \
  -H "Authorization: Bearer $TOKEN"

# Organismes avec sites
curl -X GET "http://localhost:8000/api/users/organismes/?has_sites=true" \
  -H "Authorization: Bearer $TOKEN"

# Recherche globale
curl -X GET "http://localhost:8000/api/users/sites/?search=camargue" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🛡️ **Sécurité et permissions**

### **Filtrage automatique des données**
- **Super Admin** : Voit tous organismes et sites
- **Admin Organisme** : Voit son organisme + enfants + sites gérés
- **Référent** : Voit son organisme + sites assignés
- **Utilisateur** : Voit son organisme + sites de cet organisme

### **Validation des actions**
- Création/modification selon permissions hiérarchiques
- Vérification des relations avant assignation
- Support des géométries PostGIS avec validation
- Audit automatique via middleware

### **Performance et limites**
- Pagination par défaut (20 éléments)
- Export GeoJSON limité à 100 sites
- Index géospatiaux pour requêtes performantes
- Cache Redis pour références fréquentes