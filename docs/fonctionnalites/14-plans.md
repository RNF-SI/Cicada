# 14. Module Plans de Gestion

Ce document décrit le fonctionnement du module de gestion des plans de gestion dans CICADA.

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Cycle de vie](#cycle-de-vie)
3. [Liste des plans](#liste-des-plans)
4. [Création d'un plan](#création-dun-plan)
5. [Liaison avec les sites](#liaison-avec-les-sites)
6. [Liaison avec les utilisateurs (membres et référents)](#liaison-avec-les-utilisateurs-membres-et-référents)
7. [Gestion des sites en attente](#gestion-des-sites-en-attente)
8. [Réassignation de site](#réassignation-de-site)
9. [Rédacteurs et relecteurs](#rédacteurs-et-relecteurs)
10. [Duplication d'un plan](#duplication-dun-plan)
11. [API Endpoints](#api-endpoints)

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

| Statut | Label | Description |
|--------|-------|-------------|
| `draft` | Brouillon | En cours de rédaction, non publié |
| `valide` | Actif | Plan validé et actif |
| `archive` | Inactif | Plan archivé, rendu inactif |

---

## Cycle de vie

Le cycle de vie d'un plan de gestion gère les transitions de statut, la chaîne de versions (plan parent → évaluation → plan révisé) et les actions associées.

### Transitions de statut

```
          ┌──────────────────┐
          │     Brouillon    │
          │     (draft)      │
          └───────┬──────────┘
                  │  Valider
                  ▼
          ┌──────────────────┐
   ┌─────▶│      Actif       │◀─────┐
   │      │     (valide)     │      │
   │      └───┬──────────┬───┘      │
   │          │          │          │
   │  Remettre│          │Archiver  │ Réactiver
   │  en      │          │          │
   │  brouillon          ▼          │
   │      ┌──────────────────┐      │
   │      │     Inactif      │──────┘
   │      │    (archive)     │
   │      └──────────────────┘
   │                │
   └────────────────┘
        Remettre en brouillon
```

**Transitions autorisées :**

| De | Vers | Action |
|----|------|--------|
| `draft` | `valide` | Valider le plan |
| `valide` | `draft` | Remettre en brouillon |
| `valide` | `archive` | Archiver (rend le plan inactif) |
| `archive` | `draft` | Remettre en brouillon |

> **Note** : Archiver un plan le rend **inactif**. Réactiver un plan archivé le remet en **brouillon** (statut `draft`).

### Permissions du cycle de vie

Les actions de cycle de vie (changement de statut, création d'évaluation) sont réservées à :

| Rôle | Accès |
|------|-------|
| **Référent du plan** | Peut gérer le cycle de vie des plans dont il est référent |
| **Admin organisme** | Peut gérer tous les plans de son organisme |
| **Super admin** | Peut gérer tous les plans |

Un utilisateur simple (non référent) ne peut pas modifier le statut d'un plan.

### Chaîne de versions

Un plan de gestion peut avoir un **plan parent**, formant une chaîne de versions. Chaque plan est associé à un **type de document** (nomenclature) :

| Type | Mnémonique | Description |
|------|-----------|-------------|
| Plan initial | `PLAN_INITIAL` | Premier plan de gestion |
| Évaluation mi-parcours | `EVAL_MI_PARCOURS` | Évaluation intermédiaire |
| Plan révisé | `PLAN_REVISE` | Plan révisé suite à une évaluation |

**Exemple de chaîne :**

```
Plan initial (v1.0, validé)
  └── Évaluation mi-parcours (v1.1, brouillon)
        └── Plan révisé (v2.0, brouillon)
```

### Création d'une évaluation mi-parcours

L'action "Lancer une évaluation mi-parcours" est disponible uniquement :
- Si le plan courant est **validé** (`statut = valide`)
- Si le plan courant **n'est pas lui-même une évaluation** (`type_document ≠ EVAL_MI_PARCOURS`)

L'action crée un nouveau plan avec :
- `plan_parent` = plan courant
- `type_document` = `EVAL_MI_PARCOURS`
- `statut` = `draft`
- `version` = version suivante (ex: 1.0 → 1.1)
- Copie des sites et référents du plan parent

### Timeline de versions (interface)

La page détail d'un plan affiche une **timeline verticale** des versions dans la colonne latérale, visible uniquement si la chaîne contient plus d'un élément.

Chaque noeud affiche :
- La version (ex: v1.0)
- Le type de document
- Un chip de statut (brouillon, actif, inactif)
- Un badge "actuel" pour la version courante

La version courante est mise en évidence visuellement (fond coloré, bordure latérale).

Les noeuds sont cliquables pour naviguer entre les versions.

**Boutons d'action contextuels** (visibles uniquement pour les référents, admin_og et super_admin) :

| Statut courant | Actions disponibles |
|----------------|---------------------|
| Brouillon | Valider le plan |
| Actif | Remettre en brouillon, Lancer évaluation*, Archiver |
| Inactif | Réactiver (remettre en brouillon) |

\* Uniquement pour les plans (pas les évaluations)

---

## Liste des plans

La page `/plans` affiche les plans de gestion organisés en plusieurs sections.

### Structure de la page

```
┌─────────────────────────────────────────────────────────────┐
│  Bannière avec titre et bouton "Créer un plan"              │
├─────────────────────────────────────────────────────────────┤
│  Onglets : [Actifs] [Inactifs]    [Scope Toggle]*           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Section 1 : Mes plans de gestion                           │
│  └─ Plans selon le scope sélectionné                        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Section 2 : Plans en attente de validation                 │
│  └─ Demandes d'accès en cours (pending)                     │
│  └─ Affichée uniquement si demandes en attente              │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Section 3 : Demander l'accès à un plan                     │
│  └─ Plans sans accès ou rejetés (none/rejected)             │
│  └─ Barre de recherche                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘

* Le Scope Toggle est visible uniquement pour admin_og et super_admin
```

### Scope Toggle (affichage selon le rôle)

Le toggle de scope permet de filtrer les plans affichés selon différents périmètres :

| Rôle | Scopes disponibles |
|------|-------------------|
| **Super Admin** | Mes plans, Plans de mes sites, Plans de mon organisme, Tous les plans |
| **Admin Organisme** | Mes plans, Plans de mes sites, Plans de mon organisme |
| **Référent / Utilisateur** | Mes plans, Plans de mes sites |

**Définition des scopes :**

| Scope | Label affiché | Description |
|-------|---------------|-------------|
| `mine` | **Mes plans** | Plans où l'utilisateur est membre direct (via `CorRolePlan`) |
| `sites` | **Plans de mes sites** | Plans des sites auxquels l'utilisateur est lié (via `CorRoleSite`) |
| `organisme` | **Plans de mon organisme** | Plans liés aux sites de l'organisme (admin_og+) |
| `all` | **Tous les plans** | Tous les plans accessibles (super_admin uniquement) |

> **Note** : "Mes plans" affiche les plans où l'utilisateur est directement lié via la table `CorRolePlan`, qu'il soit référent ou simple membre du plan.

### Statuts d'accès aux plans

| Statut | Description | Section affichée |
|--------|-------------|------------------|
| `granted` | Accès accordé (référent du plan, accès via site, ou demande approuvée) | Mes plans |
| `pending` | Demande d'accès en attente de validation | Plans en attente |
| `rejected` | Demande d'accès refusée (peut redemander) | Demander l'accès |
| `none` | Aucune demande faite | Demander l'accès |

### Détermination de l'accès

L'accès à un plan est automatiquement accordé (`granted`) si :
1. L'utilisateur est **super administrateur**
2. L'utilisateur est **membre du plan** (dans `CorRolePlan`, référent ou membre simple)
3. L'utilisateur a **accès à un des sites** liés au plan (via `CorRoleSite`)
4. Une **demande d'accès a été approuvée** pour ce plan

```
Accès = super_admin OU membre_plan OU membre_site OU demande_approuvée
```

Cette logique permet aux utilisateurs qui ont déjà accès à un site de voir automatiquement les plans de gestion associés sans avoir à faire de demande.

### Section "Plans en attente de validation"

Cette section apparaît uniquement si l'utilisateur a des demandes d'accès en cours.

**Colonnes du tableau :**

| Colonne | Description |
|---------|-------------|
| Nom du plan | Nom du plan de gestion |
| Période | Années début-fin du plan |
| Site | Premier site lié (+N autres si multi-sites) |
| Date de demande | Date à laquelle la demande a été faite |
| Statut | Badge "En attente" (orange) |

**Style visuel :**
- En-têtes de tableau : fond orange pâle (`rgba($secondary-orange-salmon, 0.15)`)
- Lignes alternées : fond orange très pâle
- Badge compteur : fond orange saumon, texte noir (WCAG AA)

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

## Liaison avec les utilisateurs (membres et référents)

### Principe

Similairement aux sites (qui utilisent `CorRoleSite`), les plans de gestion disposent d'une table de liaison `CorRolePlan` qui permet d'associer directement des utilisateurs à un plan, avec deux niveaux d'accès : **membre** ou **référent**.

### Modèle de données

La relation utilisateur-plan est gérée par la table `CorRolePlan` :

```
Role (1) ←→ (N) CorRolePlan (N) ←→ (1) PlanGestion
```

| Champ | Type | Description |
|-------|------|-------------|
| `id_role` | FK | Clé étrangère vers Role (utilisateur) |
| `plan_de_gestion` | FK | Clé étrangère vers PlanGestion |
| `referent` | Boolean | `true` = référent, `false` = membre simple |
| `date_association` | DateTime | Date d'association (auto) |
| `commentaire` | Text | Note optionnelle |

**Table SQL** : `general.cor_role_plan`

### Types de liens

| Type | Champ | Description | Permissions |
|------|-------|-------------|-------------|
| **Référent** | `referent=true` | Responsable du plan | Lecture, modification, gestion des membres |
| **Membre** | `referent=false` | Participant au plan | Lecture seule |

### Comparaison avec les sites

| Aspect | Sites (`CorRoleSite`) | Plans (`CorRolePlan`) |
|--------|----------------------|----------------------|
| Table | `utilisateurs.cor_role_site` | `general.cor_role_plan` |
| Champ référent | `referent` (boolean) | `referent` (boolean) |
| Champ validé | `referent_valid` | - (pas de validation) |
| Champ conservateur | `conservateur` | - (pas applicable) |

### Affichage dans l'interface

Sur la liste des plans, un badge **★ Référent** s'affiche à côté du nom du plan si l'utilisateur est référent (et non simple membre).

### Différence avec l'accès via les sites

Un utilisateur peut accéder à un plan de deux façons :

1. **Accès direct** (via `CorRolePlan`) : L'utilisateur est explicitement lié au plan
   - Visible dans le scope "Mes plans"
   - Peut être référent ou membre simple

2. **Accès indirect** (via `CorRoleSite`) : L'utilisateur est lié à un site du plan
   - Visible dans le scope "Plans de mes sites"
   - Accès en lecture par défaut

```
┌─────────────────────────────────────────────────────────────┐
│  Utilisateur                                                │
│       │                                                     │
│       ├─── CorRolePlan ──→ Plan (accès direct)              │
│       │         └─ referent: true/false                     │
│       │                                                     │
│       └─── CorRoleSite ──→ Site ──→ Plan (accès indirect)   │
│                 └─ referent: true/false                     │
└─────────────────────────────────────────────────────────────┘
```

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

## Duplication d'un plan

Un plan de gestion peut être dupliqué pour créer une copie avec des options configurables.

### Options de duplication

| Option | Description | Défaut |
|--------|-------------|--------|
| Enjeux | Copier les enjeux et facteurs clés de réussite | Oui |
| Objectifs long terme | Copier les objectifs long terme | Oui |
| Objectifs opérationnels | Copier les objectifs opérationnels | Oui |
| Sites | Copier les associations de sites | Oui |
| Référents | Copier les référents du plan | Oui |

### Workflow

1. L'utilisateur clique sur "Dupliquer" depuis la page détail du plan
2. Une modale présente les options de duplication avec un résumé du plan source
3. L'utilisateur sélectionne les éléments à copier et confirme
4. Le nouveau plan est créé en statut `draft` avec le nom "[Copie] Nom du plan original"
5. L'utilisateur est redirigé vers le nouveau plan

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

### Cycle de vie

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| `POST` | `/api/plans/plans/{id}/change-status/` | Changer le statut | Référent, admin_og, super_admin |
| `POST` | `/api/plans/plans/{id}/create-evaluation/` | Créer une évaluation mi-parcours | Référent, admin_og, super_admin |
| `POST` | `/api/plans/plans/{id}/duplicate/` | Dupliquer un plan | admin_og, super_admin |

### Gestion des sites

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/plans/plans/{id}/assign_site/` | Ajouter un site |
| `DELETE` | `/api/plans/plans/{id}/remove_site/` | Retirer un site |
| `POST` | `/api/plans/plans/{id}/replace_site/` | Remplacer un site |

### Gestion des membres et référents

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/plans/plans/{id}/assign_referent/` | Ajouter un référent |
| `DELETE` | `/api/plans/plans/{id}/remove_referent/` | Retirer un référent |
| `POST` | `/api/plans/plans/{id}/assign_member/` | Ajouter un membre |
| `DELETE` | `/api/plans/plans/{id}/remove_member/` | Retirer un membre |

**Note** : Les membres et référents sont gérés via la table `CorRolePlan`. Un référent est un membre avec `referent=true`.

#### Format de réponse (champ `membres`)

L'API retourne le champ `membres` dans les réponses de liste et détail :

```json
{
  "id_pg": 1,
  "nom": "Plan de gestion 2020-2030 - Camargue",
  "membres": [
    {
      "id_role": 1,
      "email": "admin@test.fr",
      "nom_role": "Admin",
      "prenom_role": "Super",
      "nom_complet": "Super Admin",
      "referent": true,
      "date_association": "2026-01-28T12:05:45Z",
      "commentaire": null
    },
    {
      "id_role": 2,
      "email": "user@test.fr",
      "nom_role": "Dupont",
      "prenom_role": "Marie",
      "nom_complet": "Marie Dupont",
      "referent": false,
      "date_association": "2026-01-28T12:05:45Z",
      "commentaire": null
    }
  ],
  "referents": [...]
}
```

> **Rétrocompatibilité** : Le champ `referents` (ManyToMany) est maintenu pour la compatibilité. Il contient uniquement les utilisateurs avec `referent=true`.

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
| `apps/plans/models.py` | Modèles PlanGestion, CorSitePg, CorRolePlan, CorPgFichier |
| `apps/plans/views.py` | ViewSet avec actions personnalisées |
| `apps/plans/serializers.py` | Serializers (CorRolePlanSerializer, etc.) |
| `apps/notifications/services.py` | `notify_plans_need_reassignment()` |
| `apps/core/management/commands/seeders/plans_seeder.py` | Données de test |

### Frontend

| Fichier | Description |
|---------|-------------|
| `features/plans/plan-create.component.*` | Formulaire de création |
| `features/plans/plan-detail.component.*` | Page de détail (timeline, actions cycle de vie) |
| `features/plans/plan-duplicate.component.*` | Formulaire de duplication |
| `features/plans/plans-list.component.*` | Liste des plans avec scope toggle |
| `shared/components/view-scope-toggle/` | Composant de sélection du scope |
| `shared/components/plan-version-timeline/` | Timeline de versions (cycle de vie) |
| `shared/components/modals/duplicate-plan-dialog/` | Modale de duplication |
| `core/models/admin.model.ts` | Interfaces PlanMembre, AdminPlan, PlanVersionChainItem |
| `core/services/admin.service.ts` | Méthodes changePlanStatus, createEvaluation, duplicatePlan |
| `assets/i18n/fr.json` | Traductions (plans.scope.*, plans.lifecycle.*) |

---

**Historique des mises à jour** :
- Janvier 2026 : Création du document
- Janvier 2026 : Ajout gestion des sites en attente de validation
- Janvier 2026 : Ajout réassignation de site avec notification automatique
- Janvier 2026 : Ajout système hybride rédacteurs/relecteurs
- Janvier 2026 : Ajout section "Plans en attente de validation" sur la liste des plans
- Janvier 2026 : Amélioration détermination accès (via sites liés) et gestion demandes rejetées
- Janvier 2026 : Ajout scope toggle (Mes plans / Mon organisme / Tous) selon le rôle utilisateur
- Janvier 2026 : Ajout relation membre/référent directe via `CorRolePlan` (comme `CorRoleSite` pour les sites)
- Mars 2026 : Ajout cycle de vie (statuts brouillon/actif/inactif, transitions, permissions référent/admin)
- Mars 2026 : Ajout chaîne de versions (plan parent, type document, évaluation mi-parcours)
- Mars 2026 : Ajout timeline de versions dans la page détail
- Mars 2026 : Ajout duplication de plan avec options configurables

---

← [Données de test (Seeders)](13-seeders.md) | [Index](../FONCTIONNALITES.md) | [Import en masse de sites](15-import-masse.md) →
