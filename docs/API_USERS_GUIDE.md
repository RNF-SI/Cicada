# 📖 Guide API REST Utilisateurs

## 🔗 Endpoints disponibles

### **Authentification requise**
Tous les endpoints nécessitent un token JWT dans l'en-tête :
```bash
Authorization: Bearer {access_token}
```

---

## 👥 **Gestion des utilisateurs**

### **GET /api/users/**
Liste paginée des utilisateurs avec filtres.

**Permissions :** Authentifié (filtrage automatique selon rôle)

**Paramètres de requête :**
- `page` : Numéro de page (défaut: 1)
- `page_size` : Taille de page (défaut: 20, max: 100)
- `search` : Recherche globale (email, nom, prénom, identifiant)
- `role_level` : Filtrer par niveau de rôle
- `organisme` : ID organisme
- `organisme_nom` : Nom organisme (recherche partielle)
- `active` : true/false
- `ordering` : Tri (-date_insert, email, nom_role, etc.)

**Exemple :**
```bash
GET /api/users/?search=marie&role_level=utilisateur&page_size=10
```

**Réponse :**
```json
{
  "links": {
    "next": "http://localhost:8000/api/users/?page=2",
    "previous": null
  },
  "pagination": {
    "count": 25,
    "current_page": 1,
    "total_pages": 3,
    "page_size": 10,
    "has_next": true,
    "has_previous": false
  },
  "results": [
    {
      "id_role": 2,
      "email": "marie.dupont@rnf.fr",
      "nom_role": "Dupont",
      "prenom_role": "Marie",
      "nom_complet": "Marie Dupont",
      "role_level": "utilisateur",
      "organisme": {
        "id_organisme": 1,
        "nom_organisme": "Réserves Naturelles de France"
      },
      "active": true,
      "is_staff": true,
      "date_insert": "2025-11-18T15:04:20.200522+01:00"
    }
  ]
}
```

---

### **GET /api/users/{id}/**
Détail d'un utilisateur.

**Permissions :** Son profil OU Admin de son organisme OU Super Admin

**Réponse :**
```json
{
  "id_role": 2,
  "email": "marie.dupont@rnf.fr",
  "nom_complet": "Marie Dupont",
  "role_level": "utilisateur",
  "organisme": {...},
  "sites_lies": [
    {
      "site": {
        "id_site": 1,
        "nom_site": "Réserve Naturelle de la Camargue"
      },
      "referent": true,
      "referent_valid": true,
      "conservateur": false
    }
  ],
  "permissions_info": {
    "is_super_admin": false,
    "is_admin_organisme": false,
    "is_referent": false,
    "groups": ["Utilisateurs"]
  }
}
```

---

### **POST /api/users/**
Créer un utilisateur.

**Permissions :** Admin Organisme+

**Payload :**
```json
{
  "email": "nouveau.user@example.com",
  "nom_role": "Nom",
  "prenom_role": "Prénom",
  "role_level": "utilisateur",
  "uuid_organisme": "550e8400-e29b-41d4-a716-446655440000",
  "password": "MotDePasse123!",
  "password_confirm": "MotDePasse123!",
  "active": true
}
```

**Validations métier :**
- Super admin ne peut pas appartenir à un organisme
- Admin organisme doit avoir un organisme
- Admin organisme ne peut créer que dans son organisme

---

### **PATCH /api/users/{id}/**
Modifier un utilisateur.

**Permissions :** Son profil (limité) OU Admin de son organisme OU Super Admin

**Payload :**
```json
{
  "desc_role": "Description mise à jour",
  "role_level": "referent"
}
```

**Restrictions :**
- Utilisateur ne peut pas modifier son `role_level` ou `uuid_organisme`
- Admin organisme ne peut pas créer de Super Admin

---

### **DELETE /api/users/{id}/**
Désactiver un utilisateur (soft delete).

**Permissions :** Admin Organisme+ (dans son scope)

**Restrictions :**
- Pas d'auto-suppression
- Super Admin ne peut pas être supprimé par Admin Organisme

---

## 🔐 **Actions spécialisées**

### **GET /api/users/me/**
Obtenir ses propres informations.

**Permissions :** Authentifié

**Réponse :** Identique à GET /api/users/{id}/ pour l'utilisateur connecté

---

### **POST /api/users/{id}/change-password/**
Changer le mot de passe.

**Permissions :** Son compte OU Admin de son organisme OU Super Admin

**Payload :**
```json
{
  "password": "NouveauMotDePasse123!",
  "password_confirm": "NouveauMotDePasse123!"
}
```

---

### **POST /api/users/{id}/assign-site/**
Assigner un site à un utilisateur.

**Permissions :** Admin Organisme+ (peut gérer le site)

**Payload :**
```json
{
  "site_id": 1,
  "referent": true,
  "referent_valid": true,
  "conservateur": false
}
```

---

### **DELETE /api/users/{id}/sites/{site_id}/**
Désassigner un site d'un utilisateur.

**Permissions :** Admin Organisme+ (peut gérer le site)

---

## 📊 **Statistiques**

### **GET /api/users/stats/**
Statistiques sur les utilisateurs.

**Permissions :** Admin Organisme+

**Réponse :**
```json
{
  "total_users": 25,
  "active_users": 23,
  "inactive_users": 2,
  "by_role_level": {
    "utilisateur": {"label": "Utilisateur", "count": 18},
    "referent": {"label": "Référent", "count": 5},
    "admin_og": {"label": "Administrateur Organisme", "count": 1},
    "super_admin": {"label": "Super Administrateur", "count": 1}
  },
  "by_organisme": [
    {
      "organisme": "RNF",
      "total": 12,
      "active": 11
    }
  ]
}
```

---

## 🔍 **Filtres avancés**

### **Filtres de recherche**
- `search` : Recherche dans email, nom, prénom, identifiant, nom organisme
- `email` : Email (contient)
- `nom`, `prenom` : Nom/prénom (contient)
- `role_level` : Niveau exact
- `organisme` : ID organisme exact
- `organisme_nom` : Nom organisme (contient)

### **Filtres de date**
- `created_after` : Créé après (YYYY-MM-DD)
- `created_before` : Créé avant (YYYY-MM-DD)  
- `last_login_after` : Dernière connexion après (YYYY-MM-DD)

### **Filtres booléens**
- `active` : Actif/inactif
- `is_staff` : Staff Django
- `has_organisme` : A un organisme
- `is_admin` : A des permissions d'admin
- `is_referent_any` : Est référent d'au moins un site

### **Tri**
Paramètre `ordering` :
- `email`, `-email`
- `nom_role`, `-nom_role`
- `date_insert`, `-date_insert`
- `role_level`, `-role_level`

---

## ⚡ **Exemples d'utilisation**

### **Obtenir un token et lister les users**
```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin", "password": "admin"}' \
  | jq -r '.access')

# 2. Lister les utilisateurs
curl -X GET http://localhost:8000/api/users/ \
  -H "Authorization: Bearer $TOKEN"
```

### **Créer un utilisateur**
```bash
curl -X POST http://localhost:8000/api/users/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nouveau@example.com",
    "nom_role": "Test",
    "prenom_role": "User",
    "role_level": "utilisateur",
    "password": "Password123!",
    "password_confirm": "Password123!"
  }'
```

### **Rechercher et filtrer**
```bash
# Recherche globale
curl -X GET "http://localhost:8000/api/users/?search=marie" \
  -H "Authorization: Bearer $TOKEN"

# Filtrer par rôle et organisme
curl -X GET "http://localhost:8000/api/users/?role_level=referent&organisme=1" \
  -H "Authorization: Bearer $TOKEN"

# Tri par date de création (plus récents en premier)
curl -X GET "http://localhost:8000/api/users/?ordering=-date_insert" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🛡️ **Sécurité et permissions**

### **Filtrage automatique des données**
- **Super Admin** : Voit tous les utilisateurs
- **Admin Organisme** : Voit les utilisateurs de son organisme + son profil
- **Référent/Utilisateur** : Voit seulement son profil

### **Validation des actions**
- Création/modification respecte les règles métier
- Permissions vérifiées à chaque action
- Soft delete pour préserver l'historique
- Audit automatique via middleware

### **Headers de réponse**
Chaque réponse inclut des headers d'information :
```
X-User-Role: super_admin
X-User-Organisme: 1
X-User-Permissions: {"is_super_admin": true, ...}
```