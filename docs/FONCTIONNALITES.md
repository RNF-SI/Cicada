# Explications fonctionnelles

Ce document explique le fonctionnement des principales fonctionnalités de l'application de manière conceptuelle, sans entrer dans les détails techniques du code.

## Table des matières

1. [Système de Logs](#1-système-de-logs)
2. [Notifications](#2-notifications)
3. [Validations](#3-validations)
4. [Impersonnation](#4-impersonnation)
5. [Modules](#5-modules)
6. [Gestion des Sites](#6-gestion-des-sites)
7. [Pages d'administration](#7-pages-dadministration)
8. [Tests](#8-tests)
9. [Améliorations prévues](#9-améliorations-prévues)

---

## 1. Système de Logs

### Comment ça marche

Le système de logs trace tout ce qui se passe dans l'application pour le debugging et l'audit.

### Principe du Correlation ID

Quand une requête HTTP arrive, le système génère un identifiant unique (UUID). Cet identifiant est attaché à **tous** les logs générés pendant le traitement de cette requête. Ainsi, si un bug survient, on peut filtrer les logs par cet ID et voir exactement tout ce qui s'est passé pour cette requête spécifique.

### Flux d'une requête

1. La requête arrive → le middleware génère un UUID (ex: `f4f5f562-5b94...`)
2. Ce UUID est stocké dans un espace mémoire temporaire (thread-local)
3. Chaque fois qu'un log est écrit quelque part dans le code, le système ajoute automatiquement cet UUID
4. La réponse part avec le même UUID dans un header HTTP
5. L'espace mémoire est nettoyé

### Les 3 types de logs

| Fichier | Contenu |
|---------|---------|
| `django.log` | Logs généraux - tout ce qui se passe (infos, warnings) |
| `error.log` | Erreurs uniquement - pour les identifier rapidement |
| `audit.log` | Qui a fait quoi ? Trace les actions de modification |

### L'audit

Quand un utilisateur fait un POST, PUT, PATCH ou DELETE sur certains endpoints (users, sites, plans, organismes), le middleware enregistre automatiquement :
- **Qui** : email, id de l'utilisateur
- **Quoi** : méthode HTTP, chemin de l'API
- **Quand** : timestamp
- **Résultat** : code HTTP de la réponse

---

## 2. Notifications

### Comment ça marche

Le système de notifications informe les utilisateurs des événements importants, à la fois dans l'application (cloche) et par email.

### Deux canaux de notification

| Canal | Description |
|-------|-------------|
| **In-app** | Une notification apparaît dans la cloche du header |
| **Email** | Un email est envoyé de manière asynchrone (via Celery) |

### Quand une notification est créée

1. Un événement se produit (nouvelle demande de validation, approbation, etc.)
2. Le service `NotificationService` crée un enregistrement en base avec : destinataire, type, titre, message, priorité, liens vers objets concernés
3. Si la priorité est "high" ou "critical", un email est automatiquement mis en file d'attente
4. Celery (tâche en arrière-plan) envoie l'email sans bloquer l'application

### Le polling frontend

L'application Angular interroge le serveur toutes les 30 secondes pour récupérer les nouvelles notifications. Elle utilise un paramètre `since=timestamp` pour ne récupérer que les notifications plus récentes que la dernière vérification.

### Le badge de la cloche (compteur)

Le badge affiché sur la cloche représente la **somme de deux compteurs distincts** :

| Compteur | Ce qu'il compte | Comment il diminue |
|----------|-----------------|-------------------|
| **Notifications non lues** | Nouvelles notifications (validations approuvées, associations, etc.) | Automatiquement quand l'utilisateur ouvre le menu de notifications |
| **Validations en attente** | Demandes de validation à traiter (inscriptions, accès sites, etc.) | Quand l'utilisateur **approuve ou rejette** une demande |

**Exemple :**
- Badge affiche "15"
- L'utilisateur ouvre la cloche → les notifications sont marquées comme lues
- Badge affiche maintenant "5" (les 5 validations en attente restantes)
- L'utilisateur va dans `/administration/validations` et approuve 2 demandes
- Badge affiche "3"

**Important :** Les validations en attente ne sont pas des "notifications" au sens strict. Elles représentent des demandes qui nécessitent une action de l'utilisateur (approuver/rejeter). C'est pourquoi elles ne sont pas marquées comme "lues" à l'ouverture du menu.

### Les signaux Django

Certaines notifications sont créées automatiquement quand des événements se produisent en base de données (via les signaux Django `post_save`, `post_delete`, `m2m_changed`).

### Tableau récapitulatif des notifications

Ce tableau liste **tous les cas** où une notification est envoyée dans l'application.

#### Légende

- **Destinataire** : Qui reçoit la notification
- **Type** : Type technique de la notification (voir modèle `Notification`)
- **Priorité** : `low`, `medium`, `high`, `critical`
- **Email** : ✅ = email automatique, ❌ = in-app uniquement
- **Déclencheur** : Signal Django ou appel de service

#### Notifications de validation

| Événement | Destinataire | Type | Priorité | Email | Déclencheur |
|-----------|--------------|------|----------|:-----:|-------------|
| Nouvelle demande d'inscription | Admin_og de l'organisme OU Super_admin | `validation_request` | high | ✅ | Signal `post_save` sur `ValidationRequest` |
| Inscription approuvée | Nouvel utilisateur | `welcome` + `validation_approved` | high | ✅ | Service `ValidationService.approve_registration()` |
| Inscription rejetée | Demandeur (email direct) | Email uniquement | - | ✅ | Service `ValidationService.reject_request()` |
| Demande d'accès site approuvée | Demandeur | `validation_approved` | high | ✅ | Service `ValidationService.approve_site_access()` |
| Demande d'accès plan approuvée | Demandeur | `validation_approved` | high | ✅ | Service `ValidationService.approve_plan_access()` |
| Demande référent validée | Demandeur | `validation_approved` | high | ✅ | Service `ValidationService.approve_referent_validation()` |
| Demande lien site-organisme approuvée | Admin_og demandeur | `validation_approved` | high | ✅ | Service `ValidationService.approve_site_org_link()` |
| Demande création site approuvée | Créateur du site | `validation_approved` | high | ✅ | Service `ValidationService.approve_site_creation()` |
| Demande invitation organisme approuvée | Admin_og demandeur | `validation_approved` | high | ✅ | Service `ValidationService.approve_invite_org_to_site()` |
| Demande invitation utilisateur approuvée | Admin ayant invité | `validation_approved` | high | ✅ | Service `ValidationService.approve_invite_user_to_site()` |
| Demande rejetée (tous types) | Demandeur | `validation_rejected` | high | ✅ | Service `ValidationService.reject_request()` |
| Demande déjà traitée par un autre | Autres validateurs | `info` | low | ❌ | Service `NotificationService.notify_other_validators()` |

#### Notifications d'accès modules

| Événement | Destinataire | Type | Priorité | Email | Déclencheur |
|-----------|--------------|------|----------|:-----:|-------------|
| Accès module accordé | Utilisateur ciblé | `validation_approved` | medium | ❌ | ViewSet `ValidationRequestViewSet.grant_module_access()` |
| Accès module révoqué | Utilisateur ciblé | `validation_rejected` | medium | ❌ | ViewSet `ValidationRequestViewSet.revoke_module_access()` |

#### Notifications d'associations

| Événement | Destinataire | Type | Priorité | Email | Déclencheur |
|-----------|--------------|------|----------|:-----:|-------------|
| Utilisateur ajouté à un site | Utilisateur associé | `user_associated_site` | medium | ❌ | Signal `post_save` sur `CorRoleSite` |
| Utilisateur retiré d'un site | Utilisateur retiré | `user_removed_site` | medium | ❌ | Signal `post_delete` sur `CorRoleSite` |
| Utilisateur ajouté comme référent plan | Utilisateur ajouté | `user_associated_plan` | medium | ❌ | Signal `m2m_changed` sur `PlanGestion.referents` |

#### Notifications de statut utilisateur

| Événement | Destinataire | Type | Priorité | Email | Déclencheur |
|-----------|--------------|------|----------|:-----:|-------------|
| Compte désactivé | Utilisateur désactivé | `account_deactivated` | critical | ✅ | Signal `post_save` sur `Role` (changement `active=False`) |
| Compte désactivé (info admin) | Super_admins | `account_deactivated` | high | ✅ | Signal `post_save` sur `Role` |

#### Alertes système (tâches périodiques Celery)

| Événement | Destinataire | Type | Priorité | Email | Déclencheur |
|-----------|--------------|------|----------|:-----:|-------------|
| Site orphelin (sans utilisateurs) | Super_admins + Admin_og des organismes gestionnaires | `site_orphaned` | high | ✅ | Signal `post_delete` sur `CorRoleSite` + Tâche Celery quotidienne |
| Organisme sans administrateur | Super_admins | `organisme_no_admin` | critical | ✅ | Tâche Celery quotidienne |

### Types de notifications disponibles

Le modèle `Notification` définit les types suivants :

| Type | Label | Description |
|------|-------|-------------|
| `welcome` | Bienvenue | Notification de bienvenue après inscription approuvée |
| `validation_request` | Demande de validation | Nouvelle demande à traiter |
| `validation_approved` | Validation approuvée | Demande approuvée |
| `validation_rejected` | Validation rejetée | Demande rejetée |
| `user_associated_site` | Utilisateur associé à un site | Ajout à un site |
| `user_associated_plan` | Utilisateur associé à un plan | Ajout comme référent plan |
| `user_removed_site` | Utilisateur retiré d'un site | Retrait d'un site |
| `user_removed_plan` | Utilisateur retiré d'un plan | Retrait comme référent plan |
| `account_deactivated` | Compte désactivé | Compte utilisateur désactivé |
| `account_activated` | Compte activé | Compte utilisateur réactivé |
| `site_orphaned` | Site sans utilisateurs | Alerte site orphelin |
| `organisme_no_admin` | Organisme sans administrateur | Alerte absence d'admin_og |
| `system_alert` | Alerte système | Alerte technique |
| `info` | Information | Information générale |

### Niveaux de priorité et envoi d'email

| Priorité | Envoi email automatique | Cas d'usage |
|----------|:-----------------------:|-------------|
| `low` | ❌ | Informations secondaires |
| `medium` | ❌ | Événements normaux (associations) |
| `high` | ✅ | Demandes de validation, approbations |
| `critical` | ✅ | Désactivation de compte, alertes système |

**Règle** : Les notifications avec priorité `high` ou `critical` déclenchent automatiquement l'envoi d'un email via Celery.

### Tâches Celery périodiques

| Tâche | Fréquence | Description |
|-------|-----------|-------------|
| `check_orphaned_sites` | Quotidienne | Détecte les sites sans utilisateurs |
| `check_organismes_without_admin` | Quotidienne | Détecte les organismes sans admin_og |
| `cleanup_old_notifications` | Quotidienne | Supprime les notifications lues > 90 jours |
| `cleanup_expired_pending_users` | Quotidienne | Marque comme expirées les inscriptions > 30 jours |

### Protection contre les doublons

Le système inclut une protection contre les notifications en double :
- **Associations site** : Vérification des doublons dans les 30 dernières secondes
- **Sites orphelins** : Maximum une notification par site et par semaine
- **Organismes sans admin** : Maximum une notification par organisme et par semaine

---

## 3. Validations

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
| `invite_org_to_site` | Invitation organisme | Invitation d'un organisme à rejoindre un site |
| `invite_user_to_site` | Invitation utilisateur | Invitation d'un utilisateur à rejoindre un site |

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
| `invite_org_to_site` | ❌ | ❌ | ✅ ² | ✅ ² | ✅ |
| `invite_user_to_site` | ❌ | ❌ | ✅ ² | ✅ ² | ✅ |

¹ L'utilisateur doit déjà avoir accès au site (être lié via `CorRoleSite`)
² L'utilisateur doit être référent du site concerné

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
| `invite_org_to_site` | ❌ | ❌ | ✅ ⁵ | ✅ | ⁵ Admin de l'organisme invité |
| `invite_user_to_site` | ✅ ² | ❌ | ✅ ³ | ✅ | ² Référent du site, ³ Admin org gestionnaire |

#### Résultat de chaque validation

| Type de demande | Si approuvé | Si rejeté |
|-----------------|-------------|-----------|
| `user_registration` | Compte `Role` créé depuis `PendingUser`, email de bienvenue | Email de rejet, `PendingUser` conservé (historique) |
| `site_access` | `CorRoleSite` créé (avec `referent=True` si demandé) | Notification avec motif du refus |
| `plan_access` | Utilisateur ajouté à `plan.referents` | Notification avec motif du refus |
| `module_access` | Accès accordé (vérifié via `ValidationRequest.approved`) | Notification de refus |
| `referent_validation` | `CorRoleSite.referent = True` et `referent_valid = True` | Notification avec motif du refus |
| `site_creation` | Site créé + `CorOgSite` avec l'organisme du demandeur | Notification avec motif du refus |
| `site_org_link` | `CorOgSite` créé (non principal) | Notification avec motif du refus |
| `invite_org_to_site` | `CorOgSite` créé pour l'organisme invité | Notification avec motif du refus |
| `invite_user_to_site` | `CorRoleSite` créé pour l'utilisateur invité | Notification avec motif du refus |

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

**Invitation organisme (`invite_org_to_site`)** :
1. Admins de l'organisme invité (c'est lui qui décide de rejoindre)
2. Super admins (fallback)

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

## 4. Impersonnation

### Comment ça marche

L'impersonnation permet à un super admin de "devenir" temporairement un autre utilisateur pour voir l'application comme lui, diagnostiquer des problèmes ou vérifier des permissions.

### Le flux complet

#### Démarrage

1. Le super admin va dans la liste des utilisateurs et clique "Impersonner" sur un utilisateur
2. Le frontend sauvegarde les tokens actuels de l'admin dans localStorage (pour pouvoir revenir)
3. Une requête est envoyée au backend avec l'ID de l'utilisateur cible
4. Le backend vérifie :
   - Est-ce un super admin ?
   - Ne s'impersonne-t-il pas lui-même ?
   - La cible n'est-elle pas un super admin ?
5. Un log d'audit est créé avec : qui impersonne qui, IP, navigateur, heure de début
6. De nouveaux tokens JWT sont générés pour l'utilisateur cible, mais avec des informations supplémentaires cachées dans le token : "ceci est une session d'impersonnation, l'admin original est X"
7. Le frontend remplace ses tokens par les nouveaux
8. L'admin voit maintenant l'application comme l'utilisateur cible

#### Pendant l'impersonnation

- L'interface affiche une bannière "Vous impersonnez [Nom]"
- Toutes les requêtes API utilisent le token de l'utilisateur impersonné
- L'utilisateur impersonné ne sait pas qu'il est impersonné

#### Arrêt

1. L'admin clique sur "Arrêter l'impersonnation"
2. Le frontend envoie le token actuel au backend
3. Le backend lit les informations cachées dans le token (impersonator_id)
4. Le log d'audit est mis à jour avec l'heure de fin
5. De nouveaux tokens sont générés pour l'admin original
6. Le frontend restaure le contexte de l'admin

### Sécurité

| Règle | Description |
|-------|-------------|
| Accès restreint | Seuls les super admins peuvent impersonner |
| Protection super admins | Impossible d'impersonner un autre super admin (protection contre l'escalade) |
| Traçabilité complète | Tout est tracé : qui, qui, quand, combien de temps, depuis quelle IP |

### Mode lecture seule en production

En mode **production**, les modifications (POST, PUT, PATCH, DELETE) sont **bloquées** pendant l'impersonnation. Cela permet de :
- Consulter l'application comme un utilisateur sans risque de modification
- Garantir la traçabilité : aucune action ne peut être effectuée au nom d'un autre
- Protéger les données en production

En mode **développement**, les modifications sont autorisées pour faciliter les tests.

#### Indicateurs visuels

Quand le mode lecture seule est actif, l'utilisateur voit clairement qu'il ne peut pas modifier :

| Élément | Mode normal | Mode lecture seule |
|---------|-------------|-------------------|
| **Couleur du bandeau** | Orange (warning) | Rouge (error) |
| **Badge** | Aucun | "Mode lecture seule" avec icône 🔒 |
| **Clic sur action** | Action exécutée | Message snackbar d'erreur |

#### Comportement technique

1. **Intercepteur HTTP** (`impersonation.interceptor.ts`) :
   - Intercepte toutes les requêtes sortantes
   - Bloque les méthodes POST, PUT, PATCH, DELETE si en mode lecture seule
   - Autorise toujours GET, HEAD, OPTIONS
   - Autorise certains endpoints critiques (stop-impersonation, refresh, logout)

2. **Service `ImpersonationGuardService`** :
   - Signal `isReadOnly` : true si impersonnation + modifications bloquées
   - Signal `canModify` : inverse pour faciliter les bindings
   - Méthode `checkCanModify()` : vérifie et affiche un message si bloqué

3. **Requêtes bloquées** :
   - Ne sont jamais envoyées au serveur
   - Retournent une erreur HTTP 403 locale
   - Affichent un snackbar explicatif à l'utilisateur

#### Configuration

| Mode | Fichier | `allowImpersonationModifications` | Comportement |
|------|---------|-----------------------------------|--------------|
| Développement | `environment.ts` | `true` | Modifications autorisées |
| Production | `environment.prod.ts` | `false` | Consultation uniquement |

#### Utilisation dans les composants

Pour désactiver visuellement un bouton en mode lecture seule :

```typescript
// Dans le composant
import { ImpersonationGuardService } from '@core/services/impersonation-guard.service';

readonly impersonationGuard = inject(ImpersonationGuardService);
readonly canModify = this.impersonationGuard.canModify;

// Vérification avant action
onSave() {
  if (!this.impersonationGuard.checkCanModify()) return;
  // ... continuer avec la sauvegarde
}
```

```html
<!-- Dans le template -->
<button [disabled]="!canModify()" (click)="onSave()">Enregistrer</button>
```

#### Activer les modifications en production (urgence)

Dans des situations exceptionnelles où vous devez effectuer des modifications en impersonnation en production, vous pouvez modifier temporairement la valeur de `allowImpersonationModifications` dans le fichier `environment.prod.ts` avant le build :

```typescript
// environment.prod.ts - Modification temporaire (NON recommandé)
export const environment = {
  production: true,
  allowImpersonationModifications: true  // ⚠️ À remettre à false après
};
```

**Recommandation** : Ne pas activer cette option en production. Si des modifications sont nécessaires, utilisez votre propre compte admin ou demandez à l'utilisateur de le faire lui-même.

---

## 5. Modules

### Comment ça marche

Le système distingue trois "modules" qui représentent des fonctionnalités ou ensembles de données différents.

### Plans de Gestion (module principal)

C'est le cœur de l'application. Un plan de gestion est un document opérationnel pour la conservation d'un ou plusieurs sites.

**Caractéristiques :**
- Un plan peut concerner plusieurs sites (relation many-to-many via `cor_site_pg`)
- Un plan a des référents (utilisateurs responsables)
- L'accès dépend de : être référent du plan, être référent d'un site du plan, être admin de l'organisme gestionnaire, ou être super admin

### Sites (espaces protégés)

Les sites sont les territoires physiques (réserves naturelles, parcs, etc.).

**Gestion des accès :**
- `CorRoleSite` : lie un utilisateur à un site avec des flags (referent, conservateur)
- `CorOgSite` : lie un organisme à un site (gestionnaire principal ou secondaire)
- Un utilisateur peut voir un site s'il y est lié ou si son organisme le gère

### Zonages et Inventaires (modules optionnels)

Ce sont des fonctionnalités supplémentaires qui ne sont pas accessibles par défaut.

**Logique d'accès :**
1. Un utilisateur demande l'accès via une `ValidationRequest`
2. Un super admin approuve ou refuse
3. L'accès est vérifié en regardant s'il existe une demande approuvée pour cet utilisateur et ce module
4. Pas de table dédiée : c'est la `ValidationRequest` elle-même qui fait office de "permission"

### Pourquoi cette différence ?

| Modules | Type d'accès | Raison |
|---------|--------------|--------|
| Plans et Sites | Accès granulaire | C'est le cœur métier, avec des rôles (référent, conservateur, admin) |
| Zonages / Inventaires | Accès binaire (oui/non) | Données de référence consultatives |

---

## 6. Gestion des Sites

### Comment ça marche

Le module Sites permet aux utilisateurs de visualiser, rechercher et demander l'accès aux espaces naturels protégés. Il offre également des fonctionnalités pour les référents et les administrateurs.

### Page "Mes Sites" (`/sites`)

Cette page présente un layout style GeoNature avec :
- **Carte interactive à gauche** : Affiche la localisation de tous les sites accessibles
- **Liste des sites à droite** : Tableau des sites auxquels l'utilisateur a accès

#### Fonctionnalités disponibles

| Fonctionnalité | Description |
|----------------|-------------|
| **Recherche** | Barre de recherche pour filtrer les sites par nom, type ou organisme |
| **Accès rapide** | Clic sur un site pour accéder à sa fiche détaillée |
| **Visualisation cartographique** | Zoom automatique sur les sites avec géométries disponibles |
| **Toggle de scope** | Basculer entre différents niveaux d'affichage (mes sites / sites de l'organisme / tous) |

#### Toggle de scope d'affichage (admin_og et super_admin)

Les administrateurs d'organisme et super administrateurs disposent d'un toggle permettant de changer le scope d'affichage des sites :

| Scope | Icône | Description | Accessible par |
|-------|-------|-------------|----------------|
| **Mes sites** | 👤 | Sites auxquels l'utilisateur est directement lié (via CorRoleSite) | admin_og, super_admin |
| **Mon organisme** | 🏢 | Tous les sites gérés par l'organisme de l'utilisateur (via CorOgSite) | admin_og, super_admin |
| **Tous les sites** | 🌍 | Tous les sites de l'application | super_admin uniquement |

**Comportement :**
- Le scope par défaut est "Mes sites"
- La carte et le tableau se mettent à jour automatiquement lors du changement de scope
- La pagination et la recherche s'appliquent au scope sélectionné
- Le compteur dans le badge reflète le nombre de sites du scope actuel

**Architecture réutilisable :**
Le composant `ViewScopeToggleComponent` est conçu pour être réutilisé sur d'autres modules (ex: Plans de Gestion). Il accepte des labels personnalisés et des options configurables pour s'adapter à différents contextes.

### Recherche et demande d'accès à un site

Un utilisateur peut rechercher un site existant et demander l'accès via le bouton "Rechercher ou créer un site".

#### Le flux de recherche

1. L'utilisateur ouvre le dialog de recherche
2. Il saisit au moins 2 caractères du nom du site
3. Le système affiche **tous les sites actifs** correspondants, classés en deux catégories :
   - **Sites de mon organisme** : Sites liés à l'organisme de l'utilisateur
   - **Sites d'autres organismes** : Sites gérés par d'autres organismes

#### Demande d'accès à un site de son organisme

Pour les sites liés à son organisme, l'utilisateur peut :

1. **Demander un accès simple** : Cliquer sur "Demander l'accès"
2. **Demander un accès comme référent** : Cocher "Comme référent" avant de demander

```
Utilisateur → Demande d'accès → ValidationRequest (site_access)
                                       ↓
                    Notification aux référents du site + admin_og
                                       ↓
                         Approbation → CorRoleSite créé
```

**États possibles affichés :**

| État | Icône | Description |
|------|-------|-------------|
| Accès accordé | ✓ Vert | L'utilisateur est déjà lié au site |
| Demande en cours | ⏳ Orange | Une demande est en attente de validation |
| Disponible | Bouton bleu | L'utilisateur peut demander l'accès |

### Demande de lien site-organisme

Pour les sites d'autres organismes, l'utilisateur peut demander à **lier ce site à son propre organisme**.

#### Pourquoi cette fonctionnalité ?

Certains espaces naturels sont cogérés par plusieurs organismes. Un utilisateur d'un organisme peut vouloir que son organisme soit également reconnu comme gestionnaire d'un site existant.

#### Le flux de demande

1. L'utilisateur clique sur "Lier à mon organisme" sur un site d'un autre organisme
2. Un formulaire de justification apparaît (obligatoire)
3. L'utilisateur explique pourquoi son organisme devrait être lié à ce site
4. La demande est envoyée aux administrateurs de son propre organisme

```
Utilisateur → "Lier à mon organisme" → Justification obligatoire
                                              ↓
                          ValidationRequest (site_org_link)
                                              ↓
                              Notification admin_og du demandeur
                                              ↓
                         Approbation → CorOgSite créé (non principal)
```

**Important :** C'est l'admin de l'organisme du **demandeur** qui valide, car c'est lui qui décide si son organisme doit gérer ce site.

### Création d'un nouveau site

Si le site recherché n'existe pas, l'utilisateur peut le créer :

1. Cliquer sur "Nouveau site" en bas du dialog de recherche
2. Remplir le formulaire de création (nom, type, surface, etc.)
3. Dessiner la géométrie sur la carte (polygone en GeoJSON)
4. Soumettre le formulaire

#### Détection des doublons lors de la création

Lors de la saisie du nom du site ou de l'identifiant INPN, le système recherche automatiquement les sites existants similaires pour éviter les doublons.

##### Fonctionnement

1. **Recherche automatique** : Après 500ms de saisie (debounce), le système interroge l'API `/api/sites/check-duplicates/`
2. **Deux types de correspondances** :
   - **Correspondance exacte INPN** (bloquante) : Un site avec le même identifiant INPN existe déjà
   - **Noms similaires** (informative) : Des sites avec un nom proche existent

##### Affichage des résultats

Le formulaire de création s'adapte automatiquement :

| Situation | Affichage |
|-----------|-----------|
| Aucun doublon | Formulaire standard à 2 colonnes (carte + formulaire) |
| Doublons détectés | Formulaire à 3 colonnes avec panneau "Sites existants" à droite |

##### Panneau "Sites existants"

Quand des sites similaires sont trouvés, un panneau apparaît à droite du formulaire affichant :

- **Titre** : "Sites existants"
- **Sous-titre** : "Des sites avec un nom similaire existent déjà"
- **Liste des sites** : Cartes compactes avec nom, type, identifiant INPN

##### Actions disponibles pour chaque site suggéré

L'utilisateur peut interagir avec les sites existants au lieu de créer un doublon :

| Situation | Boutons affichés |
|-----------|------------------|
| **Site géré par mon organisme** | "Demander l'accès" |
| **Site géré par un autre organisme** | "Lier mon organisme et demander l'accès" + "Lier mon organisme uniquement" |
| **J'ai déjà accès** | Badge "Accès actif" (aucune action) |

##### Description des actions

| Action | Description | Résultat |
|--------|-------------|----------|
| **Demander l'accès** | L'organisme gère déjà le site, l'utilisateur demande un accès personnel | `ValidationRequest` de type `site_access` |
| **Lier mon organisme et demander l'accès** | L'organisme ne gère pas le site, l'utilisateur demande à la fois le lien organisme-site ET son accès personnel | `ValidationRequest` de type `site_org_link` avec flag `also_request_access` |
| **Lier mon organisme uniquement** | L'organisme ne gère pas le site, l'utilisateur demande seulement le lien organisme-site (sans accès personnel) | `ValidationRequest` de type `site_org_link` |

##### Correspondance exacte INPN (bloquante)

Si l'identifiant INPN saisi correspond exactement à un site existant :

1. Une **alerte bloquante** s'affiche dans le formulaire
2. Le bouton "Créer" est **désactivé**
3. L'utilisateur **doit** choisir une action sur le site existant (lier ou demander l'accès)

```
Utilisateur saisit "FR3600013"
        ↓
API trouve le site "Réserve de Camargue" avec cet INPN
        ↓
Alerte : "Ce code INPN est déjà utilisé par un site existant"
        ↓
Boutons : [Lier mon organisme et demander l'accès] [Lier mon organisme uniquement]
```

##### Ignorer les suggestions

Si l'utilisateur est certain que son site est nouveau malgré les similarités de nom :

1. Cliquer sur "Ignorer les suggestions" en bas du panneau
2. Le panneau disparaît
3. La création peut continuer normalement

**Note** : Si l'utilisateur modifie à nouveau le nom ou l'INPN, la vérification se relance automatiquement.

#### Workflow de validation de création

La création d'un site nécessite une validation par un administrateur :

```
Utilisateur → Formulaire création → ValidationRequest (site_creation)
                                            ↓
                         Notification aux admin_og + super_admin
                                            ↓
                              Approbation → Site créé + CorOgSite
```

**Données stockées dans la demande :**
- Nom du site, type, surface, codes (local, INPN)
- Géométrie en format GeoJSON
- Caractéristiques (marin, outre-mer)
- Organisme demandeur (automatiquement lié si approuvé)

**Si approuvé :**
- Le site est créé avec les informations fournies
- Un lien `CorOgSite` est créé avec l'organisme du demandeur (comme principal)
- Le demandeur reçoit une notification de confirmation

**Si rejeté :**
- Le demandeur reçoit une notification avec le motif du refus
- Il peut refaire une demande avec des corrections

#### Sites en attente de validation

Sur la page "Mes Sites" (`/sites`), l'utilisateur voit une section spéciale affichant ses demandes de création en attente :

- **Titre** : "Sites en attente de validation"
- **Contenu** : Cartes avec le nom du site demandé et la date de la demande
- **Visibilité** : Uniquement visible si l'utilisateur a des demandes en cours

### Page détail d'un site (`/sites/:id`)

La page de détail affiche toutes les informations d'un site avec le même layout GeoNature.

#### Informations affichées

- **Carte** : Géométrie du site (polygone ou point)
- **Informations générales** : Type, surface, codes (local, INPN), caractéristiques (marin, outre-mer)
- **Organismes gestionnaires** : Liste des organismes liés au site
- **Utilisateurs du site** : Liste des utilisateurs avec leurs rôles (référent, conservateur, utilisateur)
- **Plans de gestion associés** : Plans liés à ce site

#### Actions disponibles selon le rôle

| Action | Utilisateur | Référent | Admin |
|--------|:-----------:|:--------:|:-----:|
| Voir les informations | ✅ | ✅ | ✅ |
| Modifier le site | ❌ | ✅ | ✅ |
| Gérer les utilisateurs | ❌ | ✅ | ✅ |
| Inviter un organisme | ❌ | ✅ | ✅ |
| Demander à devenir référent | ✅ | ❌ | ❌ |

### Gestion unifiée des utilisateurs du site

Le bouton "Gérer les utilisateurs" ouvre un modal unifié permettant de gérer tous les utilisateurs du site.

#### Fonctionnalités du modal

| Fonctionnalité | Description |
|----------------|-------------|
| **Info site** | Affiche le nom du site et le nombre d'organismes liés |
| **Filtre par organisme** | Dropdown pour filtrer les utilisateurs par organisme (si plusieurs organismes liés) |
| **Recherche utilisateur** | Autocomplete pour chercher parmi les utilisateurs des organismes liés |
| **Ajout comme référent** | Checkbox pour ajouter directement un utilisateur comme référent |
| **Liste des utilisateurs** | Affiche tous les utilisateurs actuels avec leurs rôles |
| **Actions par utilisateur** | Toggle référent, retirer un utilisateur |

#### Indicateurs visuels

- **Badge "Nouveau"** : Affiché à côté du nom des utilisateurs nouvellement ajoutés
- **Badge "Modifié"** : Affiché si le statut référent a été modifié
- **Animation** : Les nouveaux utilisateurs sont mis en évidence avec une bordure verte et une animation
- **Notification** : Message de confirmation affiché en haut du modal lors d'un ajout

#### Flux d'ajout d'un utilisateur

1. Le référent ouvre le modal "Gérer les utilisateurs"
2. Il filtre éventuellement par organisme
3. Il recherche l'utilisateur souhaité dans l'autocomplete
4. Il coche "Ajouter comme référent" si nécessaire
5. Il sélectionne l'utilisateur → ajout immédiat à la liste
6. Il clique sur "Enregistrer" pour sauvegarder tous les changements

**Important :** Seuls les utilisateurs appartenant à des organismes **déjà liés au site** peuvent être ajoutés directement. Pour ajouter des utilisateurs d'autres organismes, il faut d'abord inviter leur organisme.

### Invitation d'un organisme

Le bouton "Inviter" dans la section "Organismes gestionnaires" permet d'inviter un nouvel organisme à rejoindre le site.

#### Flux d'invitation

```
Référent → "Inviter" → Sélection organisme + justification
                                    ↓
                    ValidationRequest (invite_org_to_site)
                                    ↓
                      Notification à l'admin_og de l'organisme invité
                                    ↓
                         Approbation → CorOgSite créé
```

**Si approuvé :**
- Un lien `CorOgSite` est créé (non principal)
- Les utilisateurs de cet organisme peuvent maintenant être ajoutés au site
- Le référent qui a invité reçoit une notification de confirmation

### Demande pour devenir référent

Un utilisateur qui a déjà accès à un site mais n'est pas référent peut **demander à le devenir**.

#### Prérequis

- L'utilisateur doit être lié au site (avoir un accès existant)
- L'utilisateur ne doit pas déjà être référent du site

#### Ce que permet d'être référent

Le bouton "Devenir référent" affiche une infobulle explicative :

> *"En tant que référent, vous pourrez : modifier les informations du site, gérer les utilisateurs, et valider les demandes d'accès."*

#### Le flux de demande

1. L'utilisateur clique sur "Devenir référent" sur la page détail du site
2. Une `ValidationRequest` de type `referent_validation` est créée
3. Les validateurs sont notifiés

```
Utilisateur avec accès → "Devenir référent"
                                ↓
                ValidationRequest (referent_validation)
                                ↓
     Notification aux : référents actuels + admin_og + super_admin
                                ↓
              Approbation → CorRoleSite.referent = True
                           CorRoleSite.referent_valid = True
```

#### Qui peut valider ?

| Validateur | Pourquoi |
|------------|----------|
| Référents actuels du site | Ils connaissent le site et peuvent évaluer si la personne est légitime |
| Admin de l'organisme gestionnaire | Responsable de la gestion du site |
| Super admin | Fallback si aucun autre validateur |

#### États affichés sur le bouton

| État | Affichage |
|------|-----------|
| Peut demander | Bouton vert "Devenir référent" |
| Demande en cours | Bouton gris "Demande en cours" (désactivé) |
| Déjà référent | Bouton non affiché (chip "Référent" visible) |

### Droits du référent vs utilisateur simple

| Capacité | Utilisateur | Référent |
|----------|:-----------:|:--------:|
| Voir le site | ✅ | ✅ |
| Modifier les informations du site | ❌ | ✅ |
| Ajouter/retirer des utilisateurs | ❌ | ✅ |
| Valider les demandes d'accès | ❌ | ✅ |
| Créer des plans de gestion pour ce site | ❌ | ✅ |

### Récapitulatif des types de demandes liées aux sites

| Type | Code | Déclencheur | Validateurs | Résultat si approuvé |
|------|------|-------------|-------------|----------------------|
| Création de site | `site_creation` | Formulaire de création d'un nouveau site | admin_og + super_admin | Site créé + `CorOgSite` |
| Accès site | `site_access` | Demande d'accès à un site de son organisme | Référents du site + admin_og | `CorRoleSite` créé |
| Accès comme référent | `site_access` + flag | Demande d'accès avec option référent | Référents du site + admin_og | `CorRoleSite` créé avec `referent=True` |
| Lien site-organisme | `site_org_link` | Demande de lier un site externe à son organisme | admin_og du demandeur | `CorOgSite` créé |
| Invitation organisme | `invite_org_to_site` | Référent invite un organisme sur son site | admin_og de l'organisme invité | `CorOgSite` créé |
| Devenir référent | `referent_validation` | Utilisateur lié veut devenir référent | Référents + admin_og + super_admin | `CorRoleSite.referent = True` |

---

## 7. Pages d'administration

### Comment ça marche

L'application dispose d'une interface d'administration accessible à `/administration`. Cette interface permet de gérer les utilisateurs, sites, organismes, plans et validations. **Chaque rôle voit des pages et des données différentes.**

### Les rôles et niveaux d'accès

Il est important de comprendre la différence entre un **rôle** et un **niveau d'accès** :

| Terme | Type | Description |
|-------|------|-------------|
| `super_admin` | Rôle | Administrateur global de l'application |
| `admin_og` | Rôle | Administrateur d'un organisme spécifique |
| `utilisateur` | Rôle | Utilisateur standard |
| `referent` | Niveau d'accès | Un utilisateur qui est référent d'au moins un site ou un plan |

Un `utilisateur` peut avoir le niveau d'accès `referent` s'il est désigné comme référent d'un site ou d'un plan. Ce n'est pas un rôle, c'est une propriété calculée.

### Hiérarchie des droits

```
super_admin (accès total)
    ↓
admin_og (accès limité à son organisme)
    ↓
referent (accès limité à ses sites/plans)
    ↓
utilisateur (pas d'accès à l'administration)
```

### Pages disponibles et qui y a accès

| Page | URL | super_admin | admin_og | referent | utilisateur |
|------|-----|:-----------:|:--------:|:--------:|:-----------:|
| **Tableau de bord** | `/admin/dashboard` | ✅ | ❌ | ❌ | ❌ |
| **Validations** | `/admin/validations` | ✅ | ✅ | ✅ | ❌ |
| **Utilisateurs** | `/admin/utilisateurs` | ✅ | ✅ | ❌ | ❌ |
| **Organismes** | `/admin/organismes` | ✅ | ✅ | ❌ | ❌ |
| **Sites** | `/admin/sites` | ✅ | ✅ | ✅ | ❌ |
| **Plans de gestion** | `/admin/plans` | ✅ | ✅ | ✅ | ❌ |
| **Accès modules** | `/admin/modules` | ✅ | ❌ | ❌ | ❌ |

### Redirection automatique

Quand un utilisateur accède à `/administration` sans préciser de page :

| Rôle/Niveau | Redirigé vers |
|-------------|---------------|
| `super_admin` | `/admin/dashboard` |
| `admin_og` | `/admin/utilisateurs` |
| `referent` | `/admin/validations` |
| `utilisateur` | `/accueil` (pas d'accès) |

### Ce que voit chaque rôle

#### Super Admin

Le super admin a une **vue globale** sur toute l'application :
- **Tableau de bord** : Statistiques globales (nombre de plans, utilisateurs, sites, organismes)
- **Toutes les pages** : Accès complet à toutes les fonctionnalités
- **Toutes les données** : Voit tous les utilisateurs, tous les sites, tous les plans
- **Actions spéciales** : Peut impersonner des utilisateurs, octroyer/révoquer des accès modules

#### Admin Organisme (admin_og)

L'admin organisme a une **vue limitée à son organisme** :
- **Pas de tableau de bord** : Cette page n'est pas accessible
- **Utilisateurs** : Voit uniquement les utilisateurs de son organisme
- **Sites** : Voit uniquement les sites gérés par son organisme
- **Plans** : Voit uniquement les plans liés aux sites de son organisme
- **Organismes** : Peut gérer son propre organisme uniquement
- **Validations** : Voit les demandes d'inscription pour son organisme + les demandes d'accès aux sites qu'il gère

#### Référent

Le référent a une **vue limitée à ses sites/plans assignés** :
- **Pas d'accès aux utilisateurs** : Ne peut pas gérer les utilisateurs
- **Pas d'accès aux organismes** : Ne peut pas gérer les organismes
- **Sites** : Voit uniquement les sites dont il est référent
- **Plans** : Voit uniquement les plans dont il est référent
- **Validations** : Voit les demandes d'accès aux sites/plans dont il est référent

#### Utilisateur standard

- **Aucun accès** à l'administration
- Peut accéder à son **profil** et voir ses **propres demandes**
- Peut consulter les plans auxquels il a accès (lecture seule ou édition selon ses droits)

### Détail des fonctionnalités par page

#### Tableau de bord (super_admin uniquement)

Affiche des statistiques globales :
- Nombre total de plans de gestion
- Nombre de plans actifs
- Nombre d'utilisateurs
- Nombre de sites
- Nombre d'organismes

#### Validations (tous les rôles admin)

Permet de traiter les demandes en attente :
- **Filtrer** par type (inscription, accès site, accès plan, accès module) et statut
- **Voir les détails** d'une demande
- **Approuver** ou **rejeter** les demandes

Les demandes affichées dépendent du rôle :
- `super_admin` : Toutes les demandes
- `admin_og` : Inscriptions pour son organisme + accès aux sites de son organisme
- `referent` : Accès aux sites/plans dont il est référent

#### Utilisateurs (admin_og et super_admin)

Gestion des comptes utilisateurs :
- **Liste et recherche** des utilisateurs
- **Assigner** un utilisateur à un organisme
- **Lier** un utilisateur à des sites (avec option référent)
- **Activer/désactiver** un compte
- **Impersonner** (super_admin uniquement)

Filtrage des données :
- `super_admin` : Voit tous les utilisateurs
- `admin_og` : Voit uniquement les utilisateurs de son organisme

#### Organismes (admin_og et super_admin)

Gestion des organismes :
- **Liste et recherche** des organismes
- **Créer** un nouvel organisme (super_admin uniquement)
- **Modifier** les informations d'un organisme
- **Lier** des utilisateurs à l'organisme
- **Lier** des sites à l'organisme

Filtrage des données :
- `super_admin` : Voit tous les organismes
- `admin_og` : Voit uniquement son organisme

#### Sites (tous les rôles admin)

Gestion des espaces protégés :
- **Liste et recherche** des sites
- **Créer** un nouveau site
- **Modifier** les informations d'un site
- **Gérer les référents** : Assigner des utilisateurs comme référents
- **Gérer les organismes gestionnaires** : Lier des organismes au site

Filtrage des données :
- `super_admin` : Voit tous les sites
- `admin_og` : Voit les sites de son organisme
- `referent` : Voit uniquement les sites dont il est référent

#### Plans de gestion (tous les rôles admin)

Gestion des plans :
- **Liste et recherche** des plans avec statistiques
- **Filtrer** par statut (brouillon, valide, archivé)
- **Voir les détails** d'un plan
- **Gérer les sites liés** au plan (avec ordre/rang)
- **Gérer les référents** du plan
- **Valider** un plan brouillon
- **Archiver** un plan actif
- **Restaurer** un plan archivé

Filtrage des données :
- `super_admin` : Voit tous les plans
- `admin_og` : Voit les plans liés aux sites de son organisme
- `referent` : Voit uniquement les plans dont il est référent

#### Accès modules (super_admin uniquement)

Gestion des accès aux modules optionnels (zonages, inventaires) :
- **Liste** des modules disponibles
- **Rechercher** un utilisateur
- **Octroyer** l'accès à un module
- **Révoquer** un accès existant
- **Voir les demandes** d'accès en attente
- **Approuver/rejeter** les demandes

### Menu de navigation

Le menu latéral de l'administration s'adapte automatiquement au rôle de l'utilisateur connecté. Seules les pages accessibles sont affichées :

**Pour un super_admin** :
- Tableau de bord
- Validations
- Utilisateurs
- Organismes
- Sites
- Plans de gestion
- Accès modules

**Pour un admin_og** :
- Validations
- Utilisateurs
- Organismes
- Sites
- Plans de gestion

**Pour un referent** :
- Validations
- Sites
- Plans de gestion

---

## 8. Tests

### Comment ça marche

Les tests vérifient automatiquement que le code fonctionne correctement.

### Backend (pytest)

#### Les factories

Au lieu de créer manuellement des données de test, on utilise des "usines" qui génèrent des objets réalistes.

**Exemple :** `UserFactory()` crée un utilisateur avec un email unique, un nom généré aléatoirement, un mot de passe hashé. On peut personnaliser : `UserFactory(email='custom@test.fr')`.

#### Les fixtures

Ce sont des "préparations" réutilisables.

**Exemple :** `authenticated_client` fournit un client API déjà connecté avec un utilisateur. Chaque test qui en a besoin le déclare en paramètre et pytest l'injecte automatiquement.

#### Tests unitaires vs intégration

| Type | Description |
|------|-------------|
| Unitaires | Testent une fonction/classe isolément, sans base de données réelle |
| Intégration | Testent le flux complet, avec vraie base de données, vraies requêtes HTTP |

#### Déroulement d'un test d'intégration API

1. Création des données de test via factories
2. Authentification du client de test
3. Envoi d'une requête HTTP (GET, POST, etc.)
4. Vérification du code de retour et du contenu de la réponse
5. Nettoyage automatique (rollback de la base)

### Frontend (Jest)

#### Mocking

On remplace les vrais services par des faux pour isoler ce qu'on teste.

**Exemple :** pour tester un guard de route, on remplace `AuthService` par un objet qui retourne `true` ou `false` selon le test.

#### TestBed

C'est l'environnement de test Angular. Il configure les dépendances (imports, providers) comme le ferait le vrai module, mais en version test.

### CI/CD

À chaque push ou pull request sur main/develop, GitHub Actions :

1. Lance un conteneur avec PostgreSQL
2. Installe les dépendances
3. Exécute tous les tests backend
4. Exécute tous les tests frontend
5. Génère un rapport de couverture
6. Bloque le merge si des tests échouent

### Couverture

C'est le pourcentage de lignes de code exécutées par les tests.

| Stack | Couverture actuelle | Objectif |
|-------|--------------------:|----------:|
| Backend | 62% | 80% |
| Frontend | ~10% | 70% |

---

## 9. Améliorations prévues

### Interface d'administration des logs

#### Situation actuelle

Actuellement, les logs sont écrits dans des fichiers sur le serveur (`/app/logs/`). Pour les consulter, il faut :
- Avoir un accès SSH au serveur
- Utiliser des commandes comme `tail -f`, `grep`, etc.
- Connaître le format des logs et les correlation IDs

C'est suffisant pour un développeur, mais pas pratique pour un administrateur métier.

#### Options d'amélioration

**Option 1 : Interface d'administration des logs (recommandée)**

Créer une page dans l'administration (`/admin/logs`) qui permettrait aux super admins de :
- Voir les erreurs récentes dans un tableau
- Filtrer par date, niveau (ERROR, WARNING), utilisateur concerné
- Rechercher par correlation ID ou message
- Voir le détail d'une erreur avec son contexte complet

Cela nécessite :
- Une nouvelle table `t_error_logs` pour stocker les erreurs importantes en base
- Un handler de log Django qui écrit dans cette table (en plus des fichiers)
- Une vue API et un composant Angular pour l'affichage

**Option 2 : Dashboard de santé applicative**

Une page plus simple qui affiche :
- Nombre d'erreurs des dernières 24h / 7 jours
- Les 10 dernières erreurs avec leur message
- Alertes si le taux d'erreurs dépasse un seuil

**Option 3 : Notifications d'erreurs critiques**

Envoyer automatiquement une notification (et/ou email) aux super admins quand :
- Une erreur 500 se produit
- Le même type d'erreur se répète plusieurs fois
- Un utilisateur rencontre un problème bloquant

#### Recommandation pour la V1

1. **Stocker les erreurs en base** : Modifier le handler de logs pour écrire les ERROR et CRITICAL dans une table dédiée

2. **Page admin simple** : Un tableau des erreurs récentes avec :
   - Date/heure
   - Message d'erreur (tronqué)
   - Utilisateur concerné (si authentifié)
   - Chemin de la requête
   - Bouton "Voir détails" qui affiche le contexte complet

3. **Compteur dans le header admin** : Un badge sur l'icône administration indiquant le nombre d'erreurs non vues

#### Structure de la table proposée

| Champ | Type | Description |
|-------|------|-------------|
| `id` | AutoField | Clé primaire |
| `level` | CharField | ERROR, CRITICAL, WARNING |
| `message` | TextField | Message d'erreur |
| `correlation_id` | CharField | UUID de la requête |
| `user` | FK → Role | Utilisateur concerné (nullable) |
| `path` | CharField | URL de la requête |
| `method` | CharField | GET, POST, etc. |
| `exception_type` | CharField | Type d'exception Python |
| `stack_trace` | TextField | Traceback complet |
| `context` | JSONField | Données additionnelles |
| `created_at` | DateTimeField | Horodatage |
| `acknowledged` | BooleanField | Marquée comme vue |
| `acknowledged_by` | FK → Role | Admin qui a vu |

---

**Mise à jour** : Janvier 2026
