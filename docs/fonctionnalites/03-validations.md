# Validations

### Comment ça marche

Le système de validations gère les demandes qui nécessitent une approbation humaine avant d'être effectives.

### Le concept central

Une `ValidationRequest` est une demande en attente. Elle a un statut qui évolue :

```
pending → approved / rejected / cancelled
```

Chaque type de demande a des cibles et des validateurs différents.

### Les différents flux

#### Inscription utilisateur

1. Un visiteur remplit le formulaire d'inscription public
2. Ses données sont stockées temporairement dans `PendingUser` (pas encore de vrai compte)
3. Une `ValidationRequest` de type `user_registration` est créée
4. Les admins de l'organisme demandé (ou les super admins) sont notifiés
5. **Si approuvé** : le compte réel est créé depuis PendingUser, l'utilisateur reçoit un email de bienvenue
6. **Si rejeté** : PendingUser reste en base (historique), email de rejet envoyé

#### Demande d'accès à un site

1. Un utilisateur connecté demande l'accès à un site
2. Une `ValidationRequest` de type `site_access` est créée avec le site cible
3. Les référents valides du site + les admin_og des organismes gestionnaires sont notifiés
4. **Si approuvé** : un lien `CorRoleSite` est créé, l'utilisateur peut voir le site
5. **Si rejeté** : notification avec le motif du refus

#### Demande d'accès à un module

1. Un utilisateur demande l'accès à "zonages" ou "inventaires"
2. Une `ValidationRequest` de type `module_access` est créée
3. Seuls les super admins peuvent valider
4. L'accès est déterminé par l'existence d'une demande approuvée (pas de table séparée)

---

### Demande d'accès à un Plan de Gestion (détaillée)

Ce flux est plus complexe car un plan peut concerner plusieurs sites et avoir plusieurs référents.

#### 1. L'utilisateur fait sa demande

L'utilisateur navigue vers un plan (qu'il peut voir en lecture seule ou dont il a entendu parler) et clique sur "Demander l'accès" ou "Devenir référent".

Une `ValidationRequest` est créée avec :
- `request_type` = `'plan_access'`
- `status` = `'pending'`
- `requester` = l'utilisateur qui demande
- `target_plan` = le plan concerné
- `justification` = texte optionnel expliquant pourquoi il veut l'accès

#### 2. Détermination des validateurs

Le système identifie qui peut valider cette demande. Pour un accès plan, les validateurs sont (par ordre de priorité) :

| Priorité | Validateurs |
|----------|-------------|
| 1 | **Les référents actuels du plan** : utilisateurs déjà dans `plan.referents` |
| 2 | **Les référents des sites du plan** : pour chaque site lié au plan, les utilisateurs avec `referent=True` ET `referent_valid=True` |
| 3 | **Les admins des organismes gestionnaires** : pour chaque site du plan, les `admin_og` des organismes qui gèrent ces sites |
| 4 | **Fallback : les super admins** : si aucun validateur trouvé dans les catégories précédentes |

#### 3. Notification des validateurs

Chaque validateur identifié reçoit :
- Une notification in-app (priorité haute)
- Un email avec le détail de la demande

La notification contient :
- Qui demande (nom, email, organisme)
- Quel plan est concerné
- La justification fournie
- Un lien direct vers la page de validation

#### 4. Traitement par un validateur

Le validateur consulte la demande et peut :

**Approuver** :
- Il clique sur "Approuver" (commentaire optionnel)
- Le système ajoute le demandeur à `plan.referents` (relation M2M)
- Le statut passe à `'approved'`
- Le demandeur reçoit une notification "Votre demande a été approuvée"
- Les autres validateurs reçoivent une notification "La demande a été traitée par X"
- Leurs notifications originales sont marquées comme lues

**Rejeter** :
- Il clique sur "Rejeter" (commentaire obligatoire pour expliquer pourquoi)
- Le statut passe à `'rejected'`
- Le demandeur reçoit une notification avec le motif du refus
- Les autres validateurs sont informés

#### 5. Résultat pour l'utilisateur

**Si approuvé**, l'utilisateur :
- Apparaît dans la liste des référents du plan
- Peut modifier le plan (selon les permissions du rôle référent)
- Peut valider les futures demandes d'accès à ce plan
- Reçoit les notifications liées à ce plan

**Si rejeté** :
- Il peut refaire une demande plus tard avec une meilleure justification
- L'historique de la demande rejetée est conservé

#### Exemple concret

> Marie (utilisateur RNF) veut accéder au "Plan de Gestion Camargue 2024-2034"
>
> Ce plan concerne 2 sites : "Camargue" et "Étang de Vaccarès"
>
> **Validateurs identifiés :**
> - Pierre (référent actuel du plan)
> - Jean (référent du site Camargue, referent_valid=True)
> - Sophie (admin_og de RNF, qui gère le site Camargue)
>
> → Pierre, Jean et Sophie reçoivent tous une notification
>
> **Jean approuve la demande en premier :**
> - Marie est ajoutée aux référents du plan
> - Pierre et Sophie voient "Demande traitée par Jean"
> - Marie reçoit "Votre accès au plan a été approuvé"

---

### Tableau récapitulatif des validations par rôle

Ce tableau détaille **tous les types de demandes de validation**, qui peut les créer, qui peut les valider, et leur résultat.

#### Types de demandes disponibles

| Code technique | Label | Description |
|----------------|-------|-------------|
| `user_registration` | Inscription utilisateur | Demande de création de compte |
| `site_access` | Accès à un site | Demande d'accès à un site existant |
| `plan_access` | Accès à un plan | Demande d'accès/référent à un plan de gestion |
| `module_access` | Accès à un module | Demande d'accès aux modules optionnels (zonages, inventaires) |
| `referent_validation` | Devenir référent | Demande pour devenir référent d'un site |
| `site_creation` | Création de site | Demande de création d'un nouveau site |
| `site_org_link` | Lien site-organisme | Demande pour lier un site externe à son organisme |
| `site_org_unlink` | Retrait site-organisme | Demande pour retirer un organisme d'un site |
| `invite_org_to_site` | Invitation organisme | ⚠️ **Obsolète** - Les invitations d'organisme sont désormais directes (sans validation). Type conservé pour l'historique. |
| `invite_user_to_site` | Invitation utilisateur | ⚠️ **Obsolète** - Les invitations d'utilisateur sont désormais directes (sans validation). Type conservé pour l'historique. |
| `plan_site_link` | Lien plan-site | Demande pour lier un site à un plan de gestion |
| `admin_promotion` | Promotion admin_og | Demande de promotion d'un utilisateur en admin_og |
| `admin_demotion` | Rétrogradation admin_og | Demande de rétrogradation d'un admin_og en utilisateur |

#### Qui peut créer quelle demande ?

| Type de demande | Visiteur | Utilisateur | Référent | Admin_og | Super_admin |
|-----------------|:--------:|:-----------:|:--------:|:--------:|:-----------:|
| `user_registration` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `site_access` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `plan_access` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `module_access` | ❌ | ✅ | ✅ | ✅ | ❌ |
| `referent_validation` | ❌ | ✅ ¹ | ✅ ¹ | ✅ ¹ | ✅ ¹ |
| `site_creation` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `site_org_link` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `site_org_unlink` | ❌ | ❌ | ✅ ² | ✅ ² | ✅ |
| `invite_org_to_site` | ❌ | ❌ | ✅ ² | ✅ ² | ✅ | ⚠️ Action directe, plus de validation |
| `invite_user_to_site` | ❌ | ❌ | ✅ ² | ✅ ² | ✅ | ⚠️ Action directe, plus de validation |
| `plan_site_link` | ❌ | ✅ ⁴ | ✅ ⁴ | ✅ | ✅ |
| `admin_promotion` | ❌ | ❌ | ❌ | ✅ ³ | ✅ |
| `admin_demotion` | ❌ | ❌ | ❌ | ✅ ³ | ✅ |

¹ L'utilisateur doit déjà avoir accès au site (être lié via `CorRoleSite`)
² L'utilisateur doit être référent du site concerné ou pouvoir gérer le site
³ Admin_og peut demander pour les utilisateurs de son organisme uniquement
⁴ L'utilisateur doit être référent ou membre du plan, ou lié au site (référent ou membre)

#### Qui peut valider quelle demande ?

| Type de demande | Référent site | Référent plan | Admin_og | Super_admin | Condition |
|-----------------|:-------------:|:-------------:|:--------:|:-----------:|-----------|
| `user_registration` | ❌ | ❌ | ✅ ¹ | ✅ | ¹ Admin de l'organisme demandé |
| `site_access` | ✅ ² | ❌ | ✅ ³ | ✅ | ² Référent du site ciblé, ³ Admin d'un org gestionnaire |
| `plan_access` | ✅ ⁴ | ✅ | ✅ ³ | ✅ | ⁴ Référent d'un site du plan |
| `module_access` | ❌ | ❌ | ❌ | ✅ | Super admin exclusivement |
| `referent_validation` | ✅ ² | ❌ | ✅ ³ | ✅ | ² Référent du site ciblé |
| `site_creation` | ❌ | ❌ | ✅ ¹ | ✅ | ¹ Admin de l'organisme du demandeur |
| `site_org_link` | ❌ | ❌ | ✅ ¹ | ✅ | ¹ Admin de l'organisme du demandeur |
| `site_org_unlink` | ❌ | ❌ | ✅ ⁵ | ✅ | ⁵ Admin de l'organisme à retirer |
| `invite_org_to_site` | — | — | — | — | ⚠️ Plus de validation : action directe par le référent |
| `invite_user_to_site` | — | — | — | — | ⚠️ Plus de validation : action directe par le référent |
| `plan_site_link` | ✅ ⁶ | ✅ ⁷ | ✅ | ✅ | ⁶ Si demandeur=réf. plan (accord du site requis), ⁷ Si demandeur=membre (accord du plan requis) |
| `admin_promotion` | ❌ | ❌ | ❌ | ✅ | Super admin exclusivement |
| `admin_demotion` | ❌ | ❌ | ❌ | ✅ | Super admin exclusivement |

#### Résultat de chaque validation

| Type de demande | Si approuvé | Si rejeté |
|-----------------|-------------|-----------|
| `user_registration` | Compte `Role` créé depuis `PendingUser`, email de bienvenue | Email de rejet, `PendingUser` conservé (historique) |
| `site_access` | `CorRoleSite` créé (avec `referent=True` si demandé) | Notification avec motif du refus |
| `plan_access` | `CorRolePlan` créé (référent si `request_as_referent`, sinon membre) | Notification avec motif du refus |
| `module_access` | Accès accordé (vérifié via `ValidationRequest.approved`) | Notification de refus |
| `referent_validation` | `CorRoleSite.referent = True` et `referent_valid = True` | Notification avec motif du refus |
| `site_creation` | Site créé + `CorOgSite` avec l'organisme du demandeur | Notification avec motif du refus |
| `site_org_link` | `CorOgSite` créé (non principal) | Notification avec motif du refus |
| `plan_site_link` | `CorSitePg` créé, référents du plan notifiés | Notification avec motif du refus |
| `site_org_unlink` | `CorOgSite` supprimé, organisme retiré du site | Notification avec motif du refus, lien conservé |
| `invite_org_to_site` | ⚠️ **Obsolète** - L'action est désormais directe (pas de validation) | — |
| `invite_user_to_site` | ⚠️ **Obsolète** - L'action est désormais directe (pas de validation) | — |
| `admin_promotion` | `role_level` changé en `admin_og`, notification au nouvel admin | Notification avec motif du refus |
| `admin_demotion` | `role_level` changé en `utilisateur`, notification à l'ancien admin | Notification avec motif du refus |

#### Hiérarchie de validation (ordre de priorité)

Pour la plupart des demandes, le système notifie les validateurs dans un ordre de priorité. Le premier qui valide clôture la demande.

**Accès site (`site_access`)** :
1. Référents valides du site (`referent=True` ET `referent_valid=True`)
2. Admins des organismes gestionnaires du site
3. Super admins (fallback)

**Accès plan (`plan_access`)** :
1. Référents actuels du plan (`plan.referents`)
2. Référents valides des sites liés au plan
3. Admins des organismes gestionnaires des sites du plan
4. Super admins (fallback)

**Inscription (`user_registration`)** :
1. Admins de l'organisme demandé
2. Super admins (fallback si aucun admin_og)

**Création de site / Lien site-organisme** :
1. Admins de l'organisme du demandeur
2. Super admins (fallback)

**Lien plan-site (`plan_site_link`)** :
- Si le demandeur est **référent du plan** (accord du site requis) :
  1. Référents valides du site ciblé
  2. Admins des organismes gestionnaires du site
- Sinon (membre du plan, référent/membre du site) → accord du plan requis :
  1. Référents du plan
- Fallback : super admins

> **Note** : Si le demandeur est à la fois référent du plan ET du site, ou super_admin, ou admin_og+réf. site, le lien est créé **directement** sans validation.

**Retrait site-organisme (`site_org_unlink`)** :
1. Admins de l'organisme à retirer (c'est lui qui décide de quitter)
2. Super admins (fallback)

**Invitation organisme (`invite_org_to_site`)** :
> ⚠️ **Obsolète** - Les invitations sont désormais des actions directes par le référent. Pas de validation nécessaire. Des notifications sont envoyées aux admin_og des organismes concernés, aux référents du site et aux super admins.

**Changement de rôle admin (`admin_promotion`, `admin_demotion`)** :
1. Super admins uniquement (pas de fallback)

> Note : Ces demandes sont sensibles car elles affectent les droits d'administration. Seuls les super admins peuvent les valider.

#### Matrice des permissions par rôle

| Action | Utilisateur | Référent | Admin_og | Super_admin |
|--------|:-----------:|:--------:|:--------:|:-----------:|
| **Voir ses propres demandes** | ✅ | ✅ | ✅ | ✅ |
| **Voir les demandes à valider** | ❌ | ✅ ¹ | ✅ ² | ✅ |
| **Approuver une demande** | ❌ | ✅ ¹ | ✅ ² | ✅ |
| **Rejeter une demande** | ❌ | ✅ ¹ | ✅ ² | ✅ |
| **Annuler sa propre demande** | ✅ | ✅ | ✅ | ✅ |
| **Octroyer accès module (direct)** | ❌ | ❌ | ❌ | ✅ |
| **Révoquer accès module** | ❌ | ❌ | ❌ | ✅ |

¹ Limité aux demandes concernant ses sites/plans
² Limité aux demandes concernant son organisme ou ses sites

#### Statuts des demandes

| Statut | Code | Description |
|--------|------|-------------|
| En attente | `pending` | Demande créée, en attente de validation |
| Approuvée | `approved` | Demande validée par un validateur |
| Rejetée | `rejected` | Demande refusée par un validateur |
| Annulée | `cancelled` | Demande annulée par le demandeur |
| Expirée | `expired` | Demande non traitée dans le délai (inscriptions > 30 jours) |

### Protection contre les doubles validations

Quand un validateur clique sur "Approuver", le système verrouille la demande en base de données (`select_for_update`). Si un autre validateur essaie de valider en même temps, il reçoit une erreur "Déjà traitée".

---

---

← [Notifications](02-notifications.md) | [Index](../FONCTIONNALITES.md) | [Historique d'activité](04-activite.md) →
