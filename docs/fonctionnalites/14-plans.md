# 14. Module Plans de Gestion

Ce document décrit le fonctionnement du module de gestion des plans de gestion dans CICADA.

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Cycle de vie](#cycle-de-vie)
3. [Permissions](#permissions)
4. [Liste des plans](#liste-des-plans)
5. [Création d'un plan](#création-dun-plan)
6. [Liaison avec les sites](#liaison-avec-les-sites)
7. [Validation plan-site link](#validation-plan-site-link)
8. [Liaison avec les utilisateurs (membres et référents)](#liaison-avec-les-utilisateurs-membres-et-référents)
9. [Notifications liées aux plans](#notifications-liées-aux-plans)
10. [Gestion des sites en attente](#gestion-des-sites-en-attente)
11. [Réassignation de site](#réassignation-de-site)
12. [Rédacteurs et relecteurs](#rédacteurs-et-relecteurs)
13. [Duplication d'un plan](#duplication-dun-plan)
14. [Gestion depuis la page site](#gestion-depuis-la-page-site)
15. [API Endpoints](#api-endpoints)

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
```

**Transitions autorisées :**

| De | Vers | Action |
|----|------|--------|
| `draft` | `valide` | Valider le plan |
| `valide` | `draft` | Remettre en brouillon |
| `valide` | `archive` | Archiver (rend le plan inactif) |
| `archive` | `valide` | Réactiver (rend le plan actif) |

> **Note** : Archiver un plan le rend **inactif**. Réactiver un plan archivé le remet directement en **actif** (statut `valide`).

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
| Inactif | Réactiver (rend actif) |

\* Uniquement pour les plans (pas les évaluations)

---

## Permissions

### Méthode `_can_manage_plan(user, plan)`

La gestion d'un plan (sites, utilisateurs, cycle de vie) utilise une vérification objet :

```python
def _can_manage_plan(user, plan):
    """Autorisé si admin_og+ OU référent du plan spécifique."""
    if user.is_admin_organisme():
        return True
    return plan.referents.filter(pk=user.pk).exists()
```

### Matrice des permissions

| Action | Super admin | Admin organisme | Référent du plan | Membre du plan | Utilisateur |
|--------|:-----------:|:---------------:|:----------------:|:--------------:|:-----------:|
| **Consulter** (GET) | ✅ | ✅ (son org) | ✅ | ✅ | ✅ (plans validés) |
| **Créer** (POST) | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Modifier** (PATCH) | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Supprimer** (DELETE) | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Changer le statut** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Créer une évaluation** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Dupliquer** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Ajouter/retirer un site** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Ajouter/retirer un membre** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Ajouter/retirer un référent** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Demander un lien plan-site** | ✅ | ✅ | ✅ | ✅ (via validation) | ❌ |

> **Important** : La permission est vérifiée au niveau du **plan spécifique**. Un référent d'un plan A ne peut pas gérer un plan B.

### Visibilité des enjeux, indicateurs et opérations

Les enjeux, indicateurs et opérations d'un plan sont visibles par :

| Rôle | Accès |
|------|-------|
| Super admin | Tous |
| Admin organisme | Plans de son organisme |
| Membre ou référent du plan (via `CorRolePlan`) | Plans auxquels il est lié |
| Utilisateur lié à un site du plan (via `CorRoleSite`) | Plans liés à ses sites |
| Tout utilisateur | Plans validés uniquement |

> **Note** : Les membres (non-référents) du plan ont accès en lecture aux enjeux, indicateurs et opérations. Cela permet la collaboration sans donner des droits de gestion.

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
| Ajouter un site (direct) | `POST /api/plans/{id}/assign_site/` | Référent du plan, admin_og, super_admin |
| Retirer un site | `DELETE /api/plans/{id}/remove_site/` | Référent du plan, admin_og, super_admin |
| Remplacer un site | `POST /api/plans/{id}/replace_site/` | Référent du plan, admin_og, super_admin |
| Demander un lien plan-site | `POST /api/validations/request_plan_site_link/` | Référent/membre du plan, référent/membre du site, admin_og+ |

> **Note** : L'ajout direct via `assign_site` ne passe pas par le workflow de validation. Pour le workflow avec validation, voir la section [Validation plan-site link](#validation-plan-site-link).

### Interface sur la page plan

La section "Sites" de la page plan affiche :
- La liste des sites liés avec bouton "Retirer" (si `canManageLifecycle`)
- Un bouton "Gérer les sites" ouvrant la modale `LinkPlanSiteModalComponent`
- Une section **"Sites en attente de validation"** montrant les demandes `plan_site_link` en pending (bordure pointillée, badge "En attente", icône sablier)

---

## Validation plan-site link

### Principe

La liaison d'un site à un plan peut nécessiter une **validation** selon les droits du demandeur. Ce workflow permet à un référent du plan de proposer l'ajout d'un site qu'il ne gère pas, à un membre du plan de proposer un lien qui sera validé par les référents, ou à un utilisateur lié au site de proposer un lien avec un plan.

### Endpoint

`POST /api/validations/request_plan_site_link/`

**Body :**
```json
{
  "plan_id": 123,
  "site_id": 456,
  "justification": "Ce site est pertinent pour le plan car..."
}
```

### Qui peut utiliser cet endpoint ?

| Rôle | Autorisé |
|------|----------|
| Super admin | ✅ |
| Admin organisme | ✅ |
| Référent du plan | ✅ |
| Membre du plan (via `CorRolePlan`) | ✅ |
| Référent du site | ✅ |
| Membre du site (via `CorRoleSite`) | ✅ |
| Autre | ❌ (403) |

### Lien direct vs validation

Selon les droits du demandeur, le lien peut être créé **directement** (sans validation) ou soumis à **validation** :

| Demandeur | Résultat | Réponse `direct` |
|-----------|----------|:-----------------:|
| Super admin | Lien direct | `true` |
| Admin organisme + référent du site | Lien direct | `true` |
| Référent du plan + référent du site | Lien direct | `true` |
| Référent du plan (pas référent du site) | **Validation requise** | `false` |
| Membre du plan | **Validation requise** | `false` |
| Référent/membre du site (pas lié au plan) | **Validation requise** | `false` |

### Choix des validateurs

Les validateurs dépendent du rôle du demandeur :

```
┌─────────────────────────────────────────────────────────────┐
│  SI le demandeur est RÉFÉRENT du plan :                     │
│  → Le plan est d'accord, il faut l'accord du SITE          │
│  → Validateurs : référents du site + admin_og du site       │
│                                                             │
│  SINON (membre du plan, référent/membre du site) :           │
│  → Il faut l'accord du PLAN                                 │
│  → Validateurs : référents du plan                          │
│                                                             │
│  (Fallback : super_admin si aucun validateur trouvé)        │
└─────────────────────────────────────────────────────────────┘
```

### Approbation

Quand un validateur approuve la demande (`POST /api/validations/{id}/approve/`) :

1. Le lien `CorSitePg` est créé
2. Le demandeur est notifié (validation approuvée)
3. Les autres validateurs sont notifiés (demande traitée)
4. Les **référents du plan** sont notifiés que le site a été lié

### Vérifications préalables

L'endpoint vérifie avant de créer la demande :
- Le site n'est pas déjà lié au plan (`CorSitePg` existant)
- Il n'y a pas déjà une demande en attente pour ce couple plan-site
- Le demandeur a un lien avec le plan ou le site

### Affichage sur la page plan

Les demandes en attente sont affichées dans une section dédiée sous la liste des sites :

```
┌─────────────────────────────────────────────────────────────┐
│  Sites en attente de validation                             │
│  ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐                                  │
│  │ ⏳ Nom du site         │ Badge "En attente"               │
│  └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘                                  │
│  (bordure pointillée, opacité réduite)                      │
└─────────────────────────────────────────────────────────────┘
```

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

## Notifications liées aux plans

### Notifications automatiques

| Événement | Destinataires | Type | Signal/Méthode |
|-----------|---------------|------|----------------|
| Membre ajouté au plan | Référents du plan (sauf le nouveau membre) | `info` | Signal `post_save` sur `CorRolePlan` |
| Référent ajouté au plan | L'utilisateur ajouté comme référent | `user_associated_plan` | Signal `m2m_changed` sur `PlanGestion.referents` |
| Site lié au plan (direct) | Référents du plan (sauf l'utilisateur courant) | `info` | Dans `request_plan_site_link` |
| Site lié au plan (validation approuvée) | Référents du plan (sauf validateur et demandeur) | `info` | Dans `approve_plan_site_link` |
| Demande plan-site link créée | Validateurs (référents site ou plan selon le cas) | `validation_request` | Signal `post_save` sur `ValidationRequest` |
| Demande plan-site approuvée | Demandeur | `validation_approved` | Dans `approve_plan_site_link` |
| Plan à réassigner (site rejeté) | Admin_og, référents des plans concernés, super_admin | `plan_needs_reassignment` | `notify_plans_need_reassignment()` |

### Signal `notify_plan_referents_new_member`

Déclenché automatiquement lors de la création d'un `CorRolePlan` (ajout d'un membre ou référent au plan).

**Comportement :**
- Notifie chaque référent du plan (sauf le nouvel utilisateur lui-même)
- Message : "{nom} a été ajouté comme {membre/référent} du plan de gestion {nom_plan}"
- Priorité : `low`
- Lien vers la page du plan

**Fichier** : `apps/notifications/signals.py`

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

**Permissions** : Référent du plan, `admin_og` ou `super_admin`

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

## Gestion depuis la page site

### Bouton "Lier un plan"

Sur la page de détail d'un site (`/sites/:slug`), les référents du site et admin_og+ peuvent lier un plan existant au site.

**Condition d'affichage** : `canLinkPlan` — référent du site (`current_user_is_referent`) ou admin_og+.

**Workflow :**

1. L'utilisateur clique sur "Lier un plan" dans la section "Plans de gestion"
2. La modale `LinkPlanToSiteDialogComponent` s'ouvre
3. Les plans disponibles sont chargés via `adminService.getPlans({ scope: 'mine' })` (plans où l'utilisateur est membre ou référent)
4. L'utilisateur sélectionne un plan via l'autocomplete
5. L'appel passe par `validationService.requestPlanSiteLink(planId, siteId)`
6. Selon les droits, le lien est créé directement ou une demande de validation est soumise
7. Un message contextuel est affiché (lien direct vs demande en attente)

### Bouton "Demander l'accès à un plan"

Pour les utilisateurs qui ne sont pas référents du site, un bouton "Demander l'accès à un plan" est disponible. Il ouvre le dialog `AccessRequestDialogComponent` avec `type: 'plan'`.

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

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| `POST` | `/api/plans/plans/{id}/assign_site/` | Ajouter un site (direct) | Référent du plan, admin_og, super_admin |
| `DELETE` | `/api/plans/plans/{id}/remove_site/` | Retirer un site | Référent du plan, admin_og, super_admin |
| `POST` | `/api/plans/plans/{id}/replace_site/` | Remplacer un site | Référent du plan, admin_og, super_admin |

### Validation plan-site

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| `POST` | `/api/validations/request_plan_site_link/` | Demander un lien plan-site | Référent/membre du plan, référent/membre du site, admin_og+ |

### Gestion des membres et référents

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| `POST` | `/api/plans/plans/{id}/assign_referent/` | Ajouter un référent | Référent du plan, admin_og, super_admin |
| `DELETE` | `/api/plans/plans/{id}/remove_referent/` | Retirer un référent | Référent du plan, admin_og, super_admin |
| `POST` | `/api/plans/plans/{id}/assign_member/` | Ajouter un membre | Référent du plan, admin_og, super_admin |
| `DELETE` | `/api/plans/plans/{id}/remove_member/` | Retirer un membre | Référent du plan, admin_og, super_admin |

**Note** : Les membres et référents sont gérés via la table `CorRolePlan`. Un référent est un membre avec `referent=true`. Retirer un référent le passe en simple membre (l'association est conservée).

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
| `apps/plans/views.py` | ViewSet avec actions personnalisées, `_can_manage_plan()` |
| `apps/plans/views_enjeux.py` | ViewSet enjeux (accès élargi aux membres via `CorRolePlan`) |
| `apps/plans/views_indicateurs.py` | ViewSet indicateurs (idem) |
| `apps/plans/views_operations.py` | ViewSet opérations (idem) |
| `apps/plans/serializers.py` | Serializers (CorRolePlanSerializer, etc.) |
| `apps/notifications/services.py` | Validation plan-site, notifications, réassignation |
| `apps/notifications/signals.py` | Signal `notify_plan_referents_new_member` |
| `apps/notifications/views.py` | Endpoint `request_plan_site_link` |
| `apps/core/management/commands/seeders/plans_seeder.py` | Données de test |

### Frontend

| Fichier | Description |
|---------|-------------|
| `features/plans/plan-create.component.*` | Formulaire de création |
| `features/plans/plan-detail.component.*` | Page de détail (sites, utilisateurs, timeline, pending) |
| `features/plans/plan-duplicate.component.*` | Formulaire de duplication |
| `features/plans/plans-list.component.*` | Liste des plans avec scope toggle |
| `features/sites/site-detail.component.*` | Boutons lier plan / demander accès |
| `shared/components/view-scope-toggle/` | Composant de sélection du scope |
| `shared/components/plan-version-timeline/` | Timeline de versions (cycle de vie) |
| `shared/components/modals/duplicate-plan-dialog/` | Modale de duplication |
| `shared/components/modals/link-plan-site-modal/` | Modale gestion sites du plan |
| `shared/components/modals/link-plan-referent-modal/` | Modale gestion utilisateurs du plan |
| `shared/components/modals/link-plan-to-site-dialog/` | Dialog lier plan depuis page site |
| `core/models/admin.model.ts` | Interfaces PlanMembre, AdminPlan, PlanVersionChainItem |
| `core/services/admin.service.ts` | Méthodes gestion plan (status, sites, membres) |
| `core/services/validation.service.ts` | `requestPlanSiteLink()` |
| `assets/i18n/fr.json` | Traductions (plans.scope.*, plans.lifecycle.*, modals.*) |

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
- Mars 2026 : Permissions élargies aux référents du plan (assign_site, assign_referent, etc.)
- Mars 2026 : Ajout endpoints assign_member / remove_member
- Mars 2026 : Workflow validation plan-site link (lien direct vs validation selon droits)
- Mars 2026 : Notifications aux référents (nouveau membre, site lié)
- Mars 2026 : Gestion depuis la page site (lier un plan, demander accès)
- Mars 2026 : Transition archive → valide (au lieu de archive → draft)
- Mars 2026 : Visibilité enjeux/indicateurs/opérations élargie aux membres du plan

---

← [Données de test (Seeders)](13-seeders.md) | [Index](../FONCTIONNALITES.md) | [Import en masse de sites](15-import-masse.md) →
