# Gestion des Sites

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

#### Option "Demander à devenir référent"

Lors de la création d'un site, l'utilisateur peut choisir s'il souhaite devenir référent du site :

| Option | Description |
|--------|-------------|
| **Checkbox cochée** (défaut) | L'utilisateur deviendra référent du site une fois validé |
| **Checkbox décochée** | L'utilisateur aura un simple accès utilisateur au site |

Cette option permet à un utilisateur de créer un site sans forcément vouloir en être le référent (par exemple, pour préparer un site pour un collègue).

**Message affiché selon l'option :**
- Si référent : *"Vous deviendrez automatiquement référent du site une fois celui-ci validé"*
- Si utilisateur simple : *"Vous obtiendrez un accès utilisateur au site une fois celui-ci validé"*

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
- **Flag `request_as_referent`** : Indique si le demandeur veut devenir référent

**Options d'approbation pour le validateur :**

Quand le demandeur a coché "Devenir référent", le validateur voit deux boutons d'approbation :

| Bouton | Effet |
|--------|-------|
| **Approuver (référent)** | Le demandeur devient référent du site |
| **Approuver (utilisateur)** | Le demandeur obtient un simple accès utilisateur |

Cela permet au validateur de refuser le statut de référent tout en acceptant la création du site (par exemple, si le demandeur n'a pas l'expérience nécessaire pour être référent).

**Comportement du bouton "Valider" rapide :**

Dans la liste des validations, le bouton "Valider" (icône ✓) se comporte différemment selon le type de demande :

| Type de demande | Comportement du bouton rapide |
|-----------------|-------------------------------|
| Demande standard (inscription, accès plan, etc.) | Approuve directement la demande |
| Création/accès site avec demande référent | **Ouvre le dialog** pour permettre le choix référent/utilisateur |

Cette distinction garantit que le validateur fait un choix conscient lorsque l'utilisateur a demandé à devenir référent.

**Affichage dans le dialog :**

Quand le dialog s'ouvre pour une demande avec `request_as_referent=true`, une bannière informative indique clairement la demande de l'utilisateur :

> *"**Demande de l'utilisateur :** [Nom] souhaite devenir **référent** de ce site. Vous pouvez approuver la demande en tant que référent ou en tant qu'utilisateur simple."*

**Si approuvé :**
- Le site est créé avec les informations fournies
- Un lien `CorOgSite` est créé avec l'organisme du demandeur (comme principal)
- Un lien `CorRoleSite` est créé avec le statut (référent ou utilisateur) choisi par le validateur
- Le demandeur reçoit une notification de confirmation indiquant son rôle

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

Le bouton "Inviter" dans la section "Organismes gestionnaires" permet d'ajouter directement un nouvel organisme au site.

#### Flux d'invitation (direct, sans validation)

```
Référent → "Inviter" → Sélection organisme + justification (optionnelle)
                                    ↓
                        CorOgSite créé immédiatement
                                    ↓
                    Notifications envoyées aux parties prenantes
                    (admin_og des 2 organismes, référents du site, super_admin)
                                    ↓
                    Activité loguée (ActivityService)
```

**Résultat immédiat :**
- Un lien `CorOgSite` est créé (non principal)
- Les utilisateurs de cet organisme peuvent maintenant être ajoutés au site
- Les administrateurs des organismes concernés, les référents du site et les super admins sont notifiés

> **Note :** Contrairement aux demandes d'accès (`site_access`, `site_org_link`), l'invitation par un référent ne passe pas par une demande de validation. Le lien est créé directement.

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
| Retrait site-organisme | `site_org_unlink` | Demande de retirer un organisme d'un site | admin_og de l'organisme à retirer | `CorOgSite` supprimé |
| Invitation organisme | *(action directe)* | Référent ajoute un organisme sur son site | *(pas de validation)* | `CorOgSite` créé + notifications |
| Invitation utilisateur | *(action directe)* | Référent ajoute un utilisateur sur son site | *(pas de validation)* | `CorRoleSite` créé + notifications |
| Devenir référent | `referent_validation` | Utilisateur lié veut devenir référent | Référents + admin_og + super_admin | `CorRoleSite.referent = True` |

---

---

← [Modules](06-modules.md) | [Index](../FONCTIONNALITES.md) | [Pages d'administration](08-administration.md) →
