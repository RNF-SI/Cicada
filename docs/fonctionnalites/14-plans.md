# 14. Module Plans de Gestion

Ce document décrit le fonctionnement du module de gestion des plans de gestion dans CICADA.

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Création d'un plan](#création-dun-plan)
3. [Liaison avec les sites](#liaison-avec-les-sites)
4. [Gestion des sites en attente](#gestion-des-sites-en-attente)
5. [Réassignation de site](#réassignation-de-site)
6. [Rédacteurs et relecteurs](#rédacteurs-et-relecteurs)
7. [API Endpoints](#api-endpoints)

---

## Vue d'ensemble

Un **plan de gestion** est un document stratégique qui définit les objectifs et actions pour la gestion d'un ou plusieurs espaces naturels protégés (sites).

### Contraintes fondamentales

| Règle | Description |
|-------|-------------|
| Site obligatoire | Un plan doit toujours être lié à **au moins un site** |
| Multi-sites | Un plan peut être lié à plusieurs sites |
| Pas d'orphelins | Un plan ne peut pas exister sans site valide |

### Statuts d'un plan

| Statut | Description |
|--------|-------------|
| `draft` | Brouillon, en cours de rédaction |
| `valide` | Plan validé et actif |
| `archive` | Plan archivé (ancienne version) |
| `en_cours` | En cours de révision |
| `annule` | Plan annulé |

---

## Création d'un plan

### Champs obligatoires

| Champ | Type | Description |
|-------|------|-------------|
| `nom` | Texte | Nom du plan de gestion |
| `sites_ids` | Liste | IDs des sites liés (minimum 1) |
| `rang` | Entier | Numéro du plan (1er, 2ème...) |
| `ct88` | Booléen | Méthode de rédaction CT88 |
| `annee_debut` | Entier | Année de début |
| `annee_fin` | Entier | Année de fin |

### Champs optionnels

| Champ | Type | Description |
|-------|------|-------------|
| `surface` | Décimal | Surface en hectares |
| `date_validation_cspn` | Date | Date de validation CSPN |
| `id_docgestion_fcen` | Texte | Identifiant Doc'Gestion FCEN |
| `id_redacteur_type` | ID | Type d'organisme rédacteur (nomenclature) |
| `redacteur_nom` | Texte | Nom de l'organisme rédacteur |
| `redacteurs` | JSON | Liste des rédacteurs |
| `relecteurs` | JSON | Liste des relecteurs |

### Workflow de création

```
┌─────────────────────────────────────────────────────────────┐
│  Utilisateur ouvre /plans/nouveau                           │
├─────────────────────────────────────────────────────────────┤
│  1. Remplit les informations obligatoires                   │
│  2. Sélectionne un ou plusieurs sites                       │
│     └─ Option: Créer un nouveau site via modal              │
│  3. Ajoute les rédacteurs/relecteurs (optionnel)            │
│  4. Clique sur "Valider"                                    │
├─────────────────────────────────────────────────────────────┤
│  → Plan créé avec statut "draft"                            │
│  → Redirection vers la page de détail du plan               │
└─────────────────────────────────────────────────────────────┘
```

---

## Liaison avec les sites

### Modèle de données

La relation plan-site est gérée par la table `CorSitePg` :

```
PlanGestion (1) ←→ (N) CorSitePg (N) ←→ (1) Site
```

| Champ | Description |
|-------|-------------|
| `plan_de_gestion` | FK vers PlanGestion |
| `site` | FK vers Site |
| `rang` | Ordre du site dans le plan (1 = principal) |
| `commentaire` | Note optionnelle |
| `date_association` | Date d'association automatique |

### Actions disponibles

| Action | Endpoint | Permission |
|--------|----------|------------|
| Ajouter un site | `POST /api/plans/{id}/assign_site/` | admin_og |
| Retirer un site | `DELETE /api/plans/{id}/remove_site/` | admin_og |
| Remplacer un site | `POST /api/plans/{id}/replace_site/` | admin_og |

---

## Gestion des sites en attente

### Principe

Un utilisateur peut **créer un site** et l'associer **immédiatement** à un plan, même si le site est en attente de validation par un administrateur.

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  Création de plan avec site en attente                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Utilisateur crée un site via modal                      │
│     → Site créé avec statut "en attente de validation"      │
│                                                             │
│  2. Site automatiquement sélectionné dans le formulaire     │
│     → Indicateur visuel : bordure orange pointillée         │
│     → Badge : "En attente de validation"                    │
│                                                             │
│  3. Utilisateur valide la création du plan                  │
│     → Plan créé avec lien vers le site (même en attente)    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  Suite possible :                                           │
│                                                             │
│  CAS A : Admin valide le site                               │
│     → Lien plan-site confirmé ✓                             │
│     → Aucune action nécessaire                              │
│                                                             │
│  CAS B : Admin rejette le site                              │
│     → Notification envoyée aux admin_og et référents        │
│     → Message : "Plan(s) à réassigner"                      │
│     → Admin doit réassigner le plan à un autre site         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Affichage dans l'interface

Les sites en attente sont affichés différemment :

| État | Style | Sélectionnable |
|------|-------|----------------|
| Site validé | Fond blanc, bordure grise | Oui |
| Site en attente | Fond orange clair, bordure pointillée orange | Oui |
| Site sélectionné | Fond primaire léger, bordure primaire | - |
| Site en attente sélectionné | Fond orange, bordure orange pleine | - |

---

## Réassignation de site

### Quand réassigner ?

La réassignation est nécessaire quand :
- Un site lié au plan est **rejeté** par l'administrateur
- Un site est **supprimé** ou devient **invalide**
- L'utilisateur souhaite **changer** le site principal

### Notification automatique

Quand un site est rejeté, le système :

1. **Détecte** tous les plans liés au site
2. **Notifie** automatiquement :
   - Les admin_og de l'organisme concerné
   - Les référents des plans concernés
   - Les super_admins
3. **Envoie un email** avec priorité haute

### Format de la notification

```
Titre : Plans à réassigner : site [nom_site]

Message : Le site '[nom_site]' a été rejeté ou supprimé.
X plan(s) de gestion doi(ven)t être réassigné(s) à un autre site:
[liste des plans]. Un plan de gestion doit toujours être lié à
au moins un site valide.

Action URL : /plans/{plan_id}
```

### API de réassignation

**Endpoint** : `POST /api/plans/{id}/replace_site/`

**Body** :
```json
{
  "old_site_id": 123,
  "new_site_id": 456
}
```

**Réponse** :
```json
{
  "message": "Site remplacé avec succès",
  "plan_id": 42,
  "old_site_id": 123,
  "new_site_id": 456,
  "new_site_name": "Nouveau Site"
}
```

**Permissions** : `admin_og` ou `super_admin`

---

## Rédacteurs et relecteurs

### Système hybride

Les champs `redacteurs` et `relecteurs` supportent un **système hybride** :

| Type | Description | Icône |
|------|-------------|-------|
| `user` | Utilisateur de l'application (lié à un compte) | Utilisateur |
| `text` | Texte libre (personne externe sans compte) | Stylo |

### Format de stockage (JSON)

```json
[
  {
    "type": "user",
    "user_id": 123,
    "name": "Jean Dupont",
    "email": "jean.dupont@example.fr"
  },
  {
    "type": "text",
    "name": "Marie Martin (Bureau d'études XYZ)"
  }
]
```

### Interface utilisateur

L'interface utilise un **mat-chip-grid** avec autocomplete :

1. **Taper** un nom → suggestions d'utilisateurs existants
2. **Sélectionner** un utilisateur → ajout avec icône utilisateur
3. **Appuyer Entrée** (ou virgule) → ajout en texte libre avec icône stylo
4. **Cliquer sur ×** → suppression du chip

### Organisme rédacteur

Le champ `redacteur_nom` suit la même logique hybride :

| Type | Description |
|------|-------------|
| Organisme existant | Sélectionné via autocomplete sur `BibOrganismes` |
| Texte libre | Saisi manuellement si l'organisme n'existe pas |

---

## API Endpoints

### Plans de gestion

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/plans/plans/` | Liste paginée des plans |
| `POST` | `/api/plans/plans/` | Créer un plan |
| `GET` | `/api/plans/plans/{id}/` | Détail d'un plan |
| `PATCH` | `/api/plans/plans/{id}/` | Modifier un plan |
| `DELETE` | `/api/plans/plans/{id}/` | Supprimer un plan |
| `GET` | `/api/plans/plans/{id}/geojson/` | Plan au format GeoJSON |

### Gestion des sites

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/plans/plans/{id}/assign_site/` | Ajouter un site |
| `DELETE` | `/api/plans/plans/{id}/remove_site/` | Retirer un site |
| `POST` | `/api/plans/plans/{id}/replace_site/` | Remplacer un site |

### Gestion des référents

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/plans/plans/{id}/assign_referent/` | Ajouter un référent |
| `DELETE` | `/api/plans/plans/{id}/remove_referent/` | Retirer un référent |

### Filtres disponibles

| Paramètre | Description |
|-----------|-------------|
| `statut` | Filtrer par statut |
| `annee_debut` | Année de début minimum |
| `annee_fin` | Année de fin maximum |
| `site_id` | Plans liés à un site spécifique |
| `search` | Recherche textuelle |

---

## Fichiers concernés

### Backend

| Fichier | Description |
|---------|-------------|
| `apps/plans/models.py` | Modèles PlanGestion, CorSitePg |
| `apps/plans/views.py` | ViewSet avec actions personnalisées |
| `apps/plans/serializers.py` | Serializers de création/détail |
| `apps/notifications/services.py` | `notify_plans_need_reassignment()` |

### Frontend

| Fichier | Description |
|---------|-------------|
| `features/plans/plan-create.component.*` | Formulaire de création |
| `features/plans/plan-detail.component.*` | Page de détail |
| `features/plans/plans-list.component.*` | Liste des plans |
| `shared/components/modals/site-form-modal/` | Modal de création de site |

---

**Historique des mises à jour** :
- Janvier 2026 : Création du document
- Janvier 2026 : Ajout gestion des sites en attente de validation
- Janvier 2026 : Ajout réassignation de site avec notification automatique
- Janvier 2026 : Ajout système hybride rédacteurs/relecteurs
