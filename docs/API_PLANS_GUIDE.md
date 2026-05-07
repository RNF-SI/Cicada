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
| POST | `/api/plans/plans/{id}/replace_site/` | Remplacer un site dans un plan |
| POST | `/api/plans/plans/{id}/assign_referent/` | Assigner un référent |
| DELETE | `/api/plans/plans/{id}/remove_referent/` | Retirer un référent |
| POST | `/api/plans/plans/{id}/assign_member/` | Ajouter un membre |
| DELETE | `/api/plans/plans/{id}/remove_member/` | Retirer un membre |

### Cycle de vie

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/plans/plans/{id}/change-status/` | Changer le statut d'un plan |
| POST | `/api/plans/plans/{id}/create-evaluation/` | Créer une évaluation mi-parcours |
| POST | `/api/plans/plans/{id}/duplicate/` | Dupliquer un plan |

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

### 9. Gestion des membres et référents

**Ajouter un membre :**

```bash
curl -X POST http://localhost:8000/api/plans/plans/1/assign_member/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 5}'
```

**Retirer un membre :**

```bash
curl -X DELETE "http://localhost:8000/api/plans/plans/1/remove_member/?user_id=5" \
  -H "Authorization: Bearer {token}"
```

**Ajouter un référent :**

```bash
curl -X POST http://localhost:8000/api/plans/plans/1/assign_referent/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"referent_id": 3}'
```

**Retirer un référent :**

```bash
curl -X DELETE "http://localhost:8000/api/plans/plans/1/remove_referent/?referent_id=3" \
  -H "Authorization: Bearer {token}"
```

> **Note** : Retirer un référent le passe en simple membre (l'association `CorRolePlan` est conservée avec `referent=false`). Retirer un membre supprime complètement l'association.

**Permission** : Référent du plan, admin_og ou super_admin

### 11. Gestion des fichiers

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

### 12. Actions en masse

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

### Visibilité des plans (GET /api/plans/plans/)

La liste des plans visibles dépend du rôle de l'utilisateur :

| Rôle | Plans visibles |
|------|----------------|
| **Super Admin** | Tous les plans |
| **Admin Organisme** | Plans liés aux sites de son organisme |
| **Référent / Utilisateur** | Voir détail ci-dessous |

Pour un **référent** ou **utilisateur standard**, un plan est visible dès qu'**au moins une** de ces conditions est remplie :

| Condition | Description | Exemple |
|-----------|-------------|---------|
| **Assigné au site** | L'utilisateur a un rôle (`CorRoleSite`) sur un site du plan | Membre ou référent du site Camargue → voit les plans liés à Camargue |
| **Référent du plan** | L'utilisateur est nommé référent du plan directement (`PlanGestion.referents`) | Nommé référent du plan Remoray → voit ce plan même sans accès au site |
| **Membre du plan** | L'utilisateur est membre direct du plan (`CorRolePlan`) | Ajouté comme membre du plan → voit ce plan |
| **Même organisme** | Le plan est lié à un site rattaché à l'organisme de l'utilisateur | Utilisateur RNF → voit les plans des sites RNF (pour pouvoir demander l'accès) |

> **Important** : L'accès au plan et l'accès au site sont **indépendants**. Un utilisateur peut être référent d'un plan sans avoir de rôle sur le site associé. Cela permet de nommer des experts sur un plan sans leur donner accès à la gestion complète du site.

### Accès aux sites d'un plan (`current_user_has_access`)

Chaque site dans la réponse détail/liste d'un plan inclut un champ `current_user_has_access` indiquant si l'utilisateur courant peut accéder à la fiche du site. Les règles sont :

| Rôle | Condition d'accès au site |
|------|--------------------------|
| **Super Admin** | Toujours accès |
| **Admin Organisme** | Assigné directement au site (`CorRoleSite`) **ou** site lié à son organisme (`CorOgSite`) |
| **Référent / Utilisateur** | Assigné directement au site (`CorRoleSite`) uniquement |

> **Règle clé** : Seuls les **admin organisme** et **super admin** bénéficient de l'accès implicite via l'organisme (`CorOgSite`). Les utilisateurs standard doivent être assignés individuellement au site. Si l'utilisateur n'a pas accès, le frontend affiche un cadenas avec un bouton "Demander l'accès".

Le paramètre `?scope=mine` exclut la condition "même organisme" pour n'afficher que les plans sur lesquels l'utilisateur a un accès direct (utilisé par la page de duplication).

### Actions sur les plans

| Action | Permission requise |
|--------|-------------------|
| **Consulter** (GET) | Visibilité selon les règles ci-dessus |
| **Créer** (POST) | Admin organisme ou super admin |
| **Modifier** (PATCH) | Référent du plan, admin organisme ou super admin |
| **Supprimer** (DELETE) | Super admin uniquement |
| **Changer le statut** | Référent du plan spécifique, admin organisme ou super admin |
| **Créer une évaluation** | Référent du plan spécifique, admin organisme ou super admin |
| **Dupliquer** | Admin organisme ou super admin |
| **Ajouter/retirer un site** | Référent du plan, admin organisme ou super admin |
| **Ajouter/retirer un membre** | Référent du plan, admin organisme ou super admin |
| **Ajouter/retirer un référent** | Référent du plan, admin organisme ou super admin |
| **Demander un lien plan-site** | Référent/membre du plan, référent du site, admin organisme+ |

> **Note** : La permission est vérifiée au niveau du **plan spécifique** via `_can_manage_plan(user, plan)` qui vérifie `plan.referents.filter(pk=user.pk)` ou `user.is_admin_organisme()`. Un utilisateur référent d'un autre plan ne peut pas gérer un plan dont il n'est pas référent.

### Verrouillage des modifications hors brouillon (#248)

À partir du moment où un plan **n'est plus en brouillon**, **toute écriture sur le plan ou ses entités enfants est rejetée avec un statut `403`**, indépendamment du rôle de l'utilisateur (y compris super admin).

Permission DRF : `CanModifyOnlyDraftPlan` (`apps/plans/permissions.py`), appliquée à :

`PlanGestionViewSet`, `CorPgFichierViewSet`, `EnjeuViewSet`, `FacteurInfluenceViewSet`, `PressionViewSet`, `ObjectifLongTermeViewSet`, `NiveauExigenceViewSet`, `ObjectifOperationnelViewSet`, `ResultatAttenduViewSet`, `IndicateurViewSet`, `MetriqueViewSet`, `MesureViewSet`, `OperationViewSet`, `SuiviInventaireViewSet`.

**Actions exemptées** (autorisées hors brouillon) :
- Cycle de vie : `change-status`, `duplicate`, `create-evaluation`.
- Associations plan ↔ entités : `assign_site`, `remove_site`, `replace_site`, `assign_referent`, `remove_referent`, `assign_member`, `remove_member`.
- Tout endpoint de consultation (méthodes `GET`/`HEAD`/`OPTIONS`).

**Réponse type lors d'une tentative de modification** :

```json
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "detail": "Le plan de gestion associé n'est pas en brouillon. Pour modifier ce plan, repassez-le en brouillon ou créez une nouvelle version.",
  "correlation_id": "..."
}
```

**Pour modifier un plan validé/archivé** :
1. Soit `POST /api/plans/plans/{id}/change-status/` avec `{"new_status": "draft"}` pour le repasser en brouillon.
2. Soit `POST /api/plans/plans/{id}/duplicate/` ou `POST /api/plans/plans/{id}/create-evaluation/` pour créer une nouvelle version éditable.

> ℹ️ L'endpoint `/api/plans/enjeux/by-plan/{id}/` retourne désormais le champ `plan_statut`, utilisé par le frontend pour afficher la bannière « Plan verrouillé en lecture seule » et désactiver l'UI d'édition.

### Validation plan-site link

L'endpoint `POST /api/validations/request_plan_site_link/` permet de demander la liaison d'un site à un plan. Selon les droits du demandeur, le lien est créé directement ou soumis à validation :

| Demandeur | Résultat |
|-----------|----------|
| Super admin | Lien direct |
| Admin organisme + référent du site | Lien direct |
| Référent du plan + référent du site | Lien direct |
| Référent du plan (pas référent du site) | Validation par les référents/admin du site |
| Membre du plan | Validation par les référents du plan |
| Référent/membre du site (pas lié au plan) | Validation par les référents du plan |

```bash
curl -X POST http://localhost:8000/api/validations/request_plan_site_link/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"plan_id": 1, "site_id": 2}'

# Réponse (lien direct)
{"message": "Site lie au plan avec succes.", "direct": true}

# Réponse (validation requise)
{"id": 42, "message": "Votre demande de lien plan-site a ete soumise...", "direct": false}
```

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

## 🔄 Cycle de vie

### 13. Changement de statut

**POST /api/plans/plans/{id}/change-status/**

Transitions autorisées : `draft → valide`, `valide → draft`, `valide → archive`, `archive → valide`

**Permission** : Référent du plan, admin_og ou super_admin

```bash
curl -X POST http://localhost:8000/api/plans/plans/1/change-status/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"new_status": "valide"}'
```

**Réponse :**
```json
{
  "status": "success",
  "new_status": "valide",
  "message": "Statut changé avec succès"
}
```

**Erreurs possibles :**
```json
// 400 - Transition non autorisée
{"error": "Transition de draft vers archive non autorisée"}

// 403 - Permissions insuffisantes
{"detail": "Vous n'avez pas la permission de gérer ce plan."}
```

**Flux d'archivage automatique du plan précédent (#246)** :

À l'issue d'une transition `draft → valide`, le **frontend** déclenche une pop-up d'archivage si la `version_chain` du plan validé contient un autre plan encore au statut `valide`. Si l'utilisateur confirme, un second appel `change-status` est émis sur le plan précédent avec `{"new_status": "archive"}`.

Ce flux est entièrement orchestré côté frontend (helper `findPreviousValidatedPlan` dans `shared/components/modals/archive-previous-plan-dialog/`). Côté API, il s'agit donc simplement de **deux appels `change-status` consécutifs**, sans endpoint dédié.

### 14. Création d'une évaluation mi-parcours

**POST /api/plans/plans/{id}/create-evaluation/**

Crée un nouveau plan enfant de type "Évaluation mi-parcours" en brouillon. Le plan source doit être validé.

**Permission** : Référent du plan, admin_og ou super_admin

```bash
curl -X POST http://localhost:8000/api/plans/plans/1/create-evaluation/ \
  -H "Authorization: Bearer {token}"
```

**Réponse (201) :**
```json
{
  "id_pg": 5,
  "nom": "Plan de gestion 2020-2030 - Camargue",
  "slug": "plan-gestion-2020-2030-camargue-eval",
  "statut": "draft",
  "version": "1.1",
  "plan_parent_id": 1,
  "type_document_display": "Évaluation mi-parcours"
}
```

**Erreurs possibles :**
```json
// 400 - Plan non validé
{"error": "Le plan doit être validé pour créer une évaluation"}
```

### 15. Duplication d'un plan

**POST /api/plans/plans/{id}/duplicate/**

Crée une copie du plan avec les options sélectionnées.

**Permission** : admin_og ou super_admin

```bash
curl -X POST http://localhost:8000/api/plans/plans/1/duplicate/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "include_enjeux": true,
    "include_olt": true,
    "include_oo": true,
    "include_sites": true,
    "include_referents": true
  }'
```

**Réponse (201) :**
```json
{
  "id_pg": 6,
  "nom": "[Copie] Plan de gestion 2020-2030 - Camargue",
  "slug": "copie-plan-gestion-2020-2030-camargue",
  "statut": "draft"
}
```

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