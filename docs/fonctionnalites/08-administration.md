# Pages d'administration

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
| **Logs erreurs** | `/admin/logs` | ✅ | ❌ | ❌ | ❌ |

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
- **Demander une promotion/rétrogradation admin** (vers super_admin)
- **Activer/désactiver** un compte
- **Impersonner** (super_admin uniquement)

**Changement de rôle admin :**

Les admin_og et super_admin peuvent demander le changement de rôle d'un utilisateur via deux boutons dans la colonne Actions :

| Bouton | Icône | Action | Disponible pour |
|--------|-------|--------|-----------------|
| **Promotion** | ↑ (vert) | Demande de promotion en admin_og | Utilisateurs simples du même organisme |
| **Rétrogradation** | ↓ (orange) | Demande de rétrogradation en utilisateur | Admin_og du même organisme |

**Règles de visibilité des boutons :**
- On ne peut pas modifier son propre rôle
- L'utilisateur cible doit être actif
- Pour un admin_og : uniquement les utilisateurs de son organisme
- Pour un super_admin : tous les utilisateurs

**Flux de demande :**
1. L'admin clique sur le bouton promotion ou rétrogradation
2. Une modal s'ouvre avec les informations de l'utilisateur
3. L'admin saisit une justification (minimum 10 caractères)
4. La demande est envoyée aux super_admins pour validation
5. Une fois validée, le `role_level` de l'utilisateur est modifié

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

#### Logs erreurs (super_admin uniquement)

Surveillance et gestion des erreurs applicatives. Cette page permet de :

**Consulter les erreurs** :
- **Liste paginée** des erreurs avec tri par date (plus récentes en premier)
- **Filtrer** par niveau (Warning, Error, Critical), statut d'acquittement, type d'exception
- **Rechercher** dans les messages ou par ID de corrélation
- **Cliquer sur une ligne** pour voir le détail complet

**Informations affichées** :

| Colonne | Description |
|---------|-------------|
| Niveau | Warning (orange), Error (rouge), Critical (bleu-vert) |
| Message | Description de l'erreur + type d'exception si applicable |
| Chemin | URL et méthode HTTP (GET, POST, etc.) de la requête |
| Utilisateur | Qui a déclenché l'erreur (si authentifié) |
| ID Corrélation | UUID unique pour tracer la requête dans tous les logs |
| Date | Date et heure de l'erreur |
| Statut | "Non acquitté" ou "Acquitté" avec nom de l'acquitteur |

**Détail d'une erreur** :

En cliquant sur une ligne, un dialogue s'ouvre avec :
- Toutes les informations du tableau
- **Stack trace complet** : la trace d'exécution technique
- **Contexte** : données additionnelles (JSON) capturées au moment de l'erreur
- Bouton pour **acquitter** l'erreur directement depuis le détail

**Acquitter les erreurs** :

L'acquittement permet de marquer une erreur comme "vue et traitée" :
- **Acquitter une erreur** : clic sur l'icône ✓ dans la colonne Actions
- **Acquitter en lot** : bouton "Acquitter tout" pour acquitter toutes les erreurs filtrées
- L'acquittement enregistre **qui** a acquitté et **quand**

**Badge dans le menu** :

Un badge rouge apparaît à côté de "Logs erreurs" dans le menu latéral, indiquant le **nombre d'erreurs non acquittées**. Ce compteur se rafraîchit automatiquement toutes les minutes.

**Nettoyage automatique** :

Une tâche planifiée (Celery) s'exécute tous les jours à 3h du matin pour supprimer :
- Les erreurs **acquittées** de plus de **30 jours**
- Les erreurs **non acquittées** de plus de **90 jours**

**Cas d'usage typiques** :

1. **Détecter un bug** : Une erreur apparaît plusieurs fois → investiguer via le stack trace
2. **Tracer une requête** : Copier l'ID de corrélation et chercher dans les fichiers de logs serveur
3. **Nettoyer après correction** : Acquitter les erreurs une fois le bug corrigé
4. **Surveiller la santé** : Vérifier régulièrement qu'il n'y a pas d'erreurs critiques non traitées

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
- Logs erreurs

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

---

← [Gestion des Sites](07-sites.md) | [Index](../FONCTIONNALITES.md) | [RGPD](09-rgpd.md) →
