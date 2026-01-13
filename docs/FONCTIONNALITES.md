# Explications fonctionnelles

Ce document explique le fonctionnement des principales fonctionnalités de l'application de manière conceptuelle, sans entrer dans les détails techniques du code.

## Table des matières

1. [Système de Logs](#1-système-de-logs)
2. [Notifications](#2-notifications)
3. [Validations](#3-validations)
4. [Impersonnation](#4-impersonnation)
5. [Modules](#5-modules)
6. [Pages d'administration](#6-pages-dadministration)
7. [Tests](#7-tests)
8. [Améliorations prévues](#8-améliorations-prévues)

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

### Les signaux Django

Certaines notifications sont créées automatiquement quand des événements se produisent en base de données :

| Événement | Notification |
|-----------|--------------|
| Utilisateur ajouté à un site | "Vous avez été ajouté au site X" |
| Utilisateur retiré d'un site | "Vous avez été retiré du site X" |
| Site sans utilisateurs | Alerte aux super admins |
| Nouvelle demande de validation | Notification aux validateurs concernés |

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

### Qui peut valider quoi ?

Le système détermine automatiquement les validateurs selon le type de demande :

| Type de demande | Validateurs |
|-----------------|-------------|
| Inscription | Admin de l'organisme demandé, sinon super admin |
| Accès site | Référents du site + admins des organismes gestionnaires |
| Accès plan | Référents du plan + référents des sites du plan + admins org |
| Accès module | Super admin uniquement |

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

## 6. Pages d'administration

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

## 7. Tests

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

## 8. Améliorations prévues

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

**Mise à jour** : Janvier 2025
