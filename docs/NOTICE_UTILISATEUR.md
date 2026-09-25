# Notice d'utilisation — CICADA

**Application de gestion des plans de gestion d'espaces naturels protégés**

| | |
|---|---|
| **Version de la notice** | [2.0 (remplace la version 1.0 de juin 2026)]{.nouveau} |
| **Date** | [Septembre 2026]{.nouveau} |
| **Public** | Gestionnaires d'espaces naturels, administrateurs CICADA |

::: nouveau
> 🖍️ **Note de relecture — à retirer avant diffusion**
> Les passages **en violet** sont **nouveaux ou modifiés** par rapport à la version 1.0 de
> juin 2026. Tout le reste est inchangé. La section « Ce qui a changé depuis juin 2026 » résume
> les évolutions. Pour retirer la couleur une fois la relecture terminée, il suffit de modifier le
> style « Nouveauté car » dans Word (couleur automatique).
:::

> 📸 **Capture 1 — Page de garde / écran d'accueil** \
> **Écran :** page d'accueil de CICADA (utilisateur non connecté), avec le logo et les boutons « Créer un compte » et « Se connecter ». \
> **État à reproduire :** affichage public, avant connexion. \
> **À mettre en évidence :** le logo CICADA, le titre de l'application [et le bandeau des partenaires en bas de page (« Avec le soutien de »)]{.nouveau}.

---

## Comment lire ce document

Cette notice rassemble **quatre guides** dans un seul document. Chacun s'adresse à un profil
d'utilisateur différent. Les profils sont **cumulatifs** : un administrateur peut faire tout ce
que fait un utilisateur simple, **plus** les fonctions propres à son rôle.

| Profil | À qui ça s'adresse | Où lire |
|--------|--------------------|---------|
| **Utilisateur** | Toute personne disposant d'un compte | Partie 1 (base commune à tous) |
| **Administrateur de plan de gestion** | Personne chargée de saisir et suivre un plan (référent du plan) | Partie 2 (+ Partie 1) |
| **Administrateur de sites** | Administrateur d'un organisme : gère les utilisateurs et les sites de sa structure | Partie 3 (+ Parties 1 et 2) |
| **Administrateur de l'application** | Super administrateur : pilote l'ensemble de l'outil | Partie 4 (+ tout le reste) |

::: nouveau
> ℹ️ **Le rédacteur général**
> Un profil intermédiaire existe entre l'administrateur d'organisme et le super administrateur :
> le **rédacteur général**. Il peut consulter et modifier **tous les plans de gestion et tous les
> sites** de l'instance, quel que soit l'organisme. Il utilise les Parties 1 à 3 de cette notice,
> sur un périmètre élargi. Ce rôle est attribué par le super administrateur (voir Partie 4).
:::

**Important :** pour ne pas répéter les mêmes explications, les fonctions de base (se connecter,
gérer son profil, recevoir des notifications, consulter sites et plans, demander un accès[,
explorer les données]{.nouveau}) ne sont décrites **qu'une seule fois, dans la Partie 1**. Les
parties suivantes y renvoient et ne détaillent que ce qui est propre à chaque rôle
d'administration.

### Les modules de CICADA aujourd'hui

::: nouveau
À ce jour, CICADA propose :

- la **saisie et le suivi des plans de gestion** ;
- le module **Mes inventaires et suivis**, qui recense les inventaires et suivis scientifiques ;
- l'**exploration des données des plans de gestion**, ouverte à tout utilisateur connecté
  (voir Partie 1).

Le module **Zonages réglementaires** est en cours de développement : il est présenté en fin de
document, dans la section « Modules à venir ».
:::

### Une phase de démarrage particulière

Lors des premiers mois d'utilisation, les gestionnaires vont d'abord **saisir dans CICADA un plan
de gestion qui existe déjà** (rédigé auparavant sous une autre forme). Dans ce contexte, certaines
informations « ne rentrent pas parfaitement dans les cases » prévues par l'outil. Pour vous aider,
des encadrés **« Cas d'usage »** sont disposés tout au long de la notice : ils décrivent une
situation concrète et laissent un espace pour y consigner la marche à suivre retenue par votre
réseau. Ces encadrés sont **à compléter** au fur et à mesure.

[Lorsque l'outil propose déjà un mécanisme adapté à la situation, il est indiqué dans l'encadré
sous la mention **« Ce que propose CICADA »**. La doctrine à appliquer reste à compléter par votre
réseau.]{.nouveau}

> 💡 **Comment reconnaître les encadrés**
> - Les encadrés **📸 Capture** indiquent où insérer une image et ce qu'elle doit montrer.
> - Les encadrés **💡 Cas d'usage** posent une situation et laissent une zone de réponse à remplir.

---

::: nouveau
## Ce qui a changé depuis juin 2026

Principales évolutions intégrées dans cette version de la notice :

**Pour tous les utilisateurs**

- Nouveau module **Exploration des données des plans de gestion** (Partie 1.10).
- Inscription : l'**identifiant de connexion** est désormais obligatoire ; possibilité de
  **demander la création de son organisme** s'il n'existe pas encore.
- Cloche de notifications : le compteur ne compte plus que les **notifications non lues** ; les
  validations en attente sont signalées par une pastille rouge.
- Page Activité : l'onglet « Notifications » a été retiré.
- Mes demandes : pour une demande en attente, on voit **qui peut la valider**.
- Sites : le créateur d'un site en attente peut le **modifier** ou **annuler la demande**.
- Tout utilisateur lié à un plan en consulte **tout le contenu en lecture seule** ; les **suivis**
  et les **exports** sont en revanche réservés aux référents et aux administrateurs.
- Le statut « Archivé » s'appelle désormais **« Terminé »**.

**Pour les administrateurs de plan de gestion**

- Nouvelle rubrique **Paramétrage** (paramètres du plan, postes / ressources humaines).
- **Import d'un plan depuis un fichier Excel** (arborescence et actions), avec correction des
  erreurs directement à l'écran.
- Nouvelle rubrique **Exports** (Word et Excel).
- Cycle de vie revu : fenêtre « Modifier ce plan validé » qui propose une nouvelle version,
  extension de durée sous forme de nouvelle version, **validations administratives** (CSRPN,
  comité, arrêté) réservées aux réserves naturelles et saisies via un badge.
- Création d'un plan : **rattachement automatique au plan du rang précédent**.
- Saisie : boutons **« Je n'ai pas de … »**, **numéros fixés manuellement**, priorité « Non
  définie », **patrimoine géologique** détaillé, recherche dans les **synonymes TaxRef**, habitat
  **hors HabRef**, **métriques à plusieurs blocs** (ET / OU), grilles Chiffre / Texte.
- **Lier ou copier** un élément (facteur, objectif, résultat attendu, action, indicateur) ;
  déplacer par **glisser-déposer**.
- Actions : **modes de ventilation budgétaire**, temps de travail **par poste**, protocoles
  standardisés (dont **MhéO**), **fiche action** imprimable et exportable.
- Suivis : **planification mensuelle**, pages **globales** d'un indicateur et d'une action,
  **forçage manuel** d'un résultat, saisie d'une action **non prévue**, **exports** des tableaux,
  **Bilan de la gestion** entièrement refondu.

**Pour les administrateurs de sites**

- **Import en masse de sites** désormais accessible à l'administrateur d'organisme, avec
  rattachement de chaque site à son organisme et à ses référents.
- Page **Orphelins** : sites sans utilisateur et plans sans site.
- Validations : la fenêtre indique si l'**organisme a déjà un administrateur**.

**Pour les administrateurs de l'application**

- Promotion d'un administrateur d'organisme **sans passer par une demande**.
- Nouvelle page **Logs serveur**.
- Paramètres : **couleur du bandeau**, **logo de la structure**, **couleur des exports**, champ
  **ID Doc'Gestion FCEN**, **API publique** des métadonnées, **partage avec l'exploration
  nationale**.
- **Numéro de version** affiché en bas du menu d'administration.
:::

---

## Sommaire

1. **Partie 1 — Notice Utilisateur** *(base commune à tous les profils)*
2. **Partie 2 — Notice Administrateur de plan de gestion**
3. **Partie 3 — Notice Administrateur de sites**
4. **Partie 4 — Notice Administrateur de l'application**
5. **Modules à venir**

---
---

# Partie 1 — Notice Utilisateur

> **À qui s'adresse cette notice ?**
> À toute personne possédant un compte CICADA. Elle décrit les fonctions disponibles pour
> **consulter** l'information et **gérer son compte**. C'est le socle commun : les administrateurs
> doivent aussi connaître cette partie.
>
> **Ce que vous pouvez faire en tant qu'utilisateur :**
> - vous connecter et gérer votre compte ;
> - consulter les sites et les plans de gestion auxquels vous avez accès ;
> - demander l'accès à un site, à un plan ou à un module ;
> - suivre vos demandes et recevoir des notifications[ ;]{.nouveau}
> - [explorer les données des plans de gestion validés.]{.nouveau}

## 1.1 Se connecter et créer un compte

### Se connecter

Rendez-vous sur la page d'accueil de CICADA et cliquez sur **Se connecter**. Saisissez votre
identifiant (ou votre adresse e-mail) et votre mot de passe, puis validez.

> 📸 **Capture 2 — Page de connexion** \
> **Écran :** formulaire de connexion (champ « Identifiant ou email », champ mot de passe, bouton « Se connecter »). \
> **À mettre en évidence :** les deux champs et le bouton de connexion.

### Créer un compte

Si vous n'avez pas encore de compte, cliquez sur **Créer un compte** depuis l'accueil. Remplissez
le formulaire : prénom, nom, e-mail, [**identifiant** (obligatoire : c'est le nom de connexion que
vous pourrez utiliser à la place de votre e-mail, par exemple « j.dupont »)]{.nouveau},
**organisme** de rattachement, mot de passe (au moins 8 caractères). Une zone facultative vous
permet d'indiquer le motif de votre demande.

::: nouveau
**Votre organisme n'est pas dans la liste ?** Cliquez sur **« Mon organisme n'existe pas dans la
liste ? Le créer »** et renseignez son nom (obligatoire) et ses coordonnées. Une demande de
création d'organisme est alors envoyée à l'administrateur, en plus de votre demande de compte :
les deux sont validées séparément.
:::

Votre demande **n'est pas immédiate** : elle doit être validée par un administrateur de votre
organisme. Une fois le formulaire envoyé, une page vous confirme que votre **inscription est en
attente**. Vous recevrez un e-mail dès que votre compte sera activé.

> 📸 **Capture 3 — Formulaire d'inscription** \
> **Écran :** formulaire « Inscription » avec les champs identifiant et organisme, et le message indiquant que la demande sera validée par un administrateur. \
> **À mettre en évidence :** les champs « Identifiant » et « Organisme », [le lien « Mon organisme n'existe pas dans la liste ? Le créer »]{.nouveau} et le message d'information sur la validation.

### Se déconnecter

Cliquez sur votre nom en haut à droite, puis sur **Déconnexion**.

> 💡 **Cas d'usage — Je ne connais pas mon organisme dans la liste** \
> **Situation :** au moment de l'inscription, l'organisme auquel je suis rattaché n'apparaît pas dans la liste proposée. \
> [**Ce que propose CICADA :** le lien « Le créer » envoie une demande de création d'organisme en même temps que la demande de compte.]{.nouveau} \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

## 1.2 L'écran d'accueil

Une fois connecté, l'accueil vous souhaite la bienvenue et affiche des **tuiles de navigation**
vers les différents modules auxquels vous avez accès : [**Mes plans de gestion**, **Mes sites**,
**Mes inventaires et suivis**]{.nouveau} (et, si l'accès vous a été donné, **Zonages
réglementaires**). Cliquez sur une tuile pour ouvrir le module correspondant.

[Au-dessus des tuiles, un grand bandeau **« Exploration des données »** ouvre le module
d'exploration (voir 1.10).]{.nouveau}

> 📸 **Capture 4 — Accueil connecté avec les tuiles** \
> **Écran :** page d'accueil après connexion, avec le message de bienvenue, [le bandeau « Exploration des données »]{.nouveau} et les tuiles de navigation. \
> **À mettre en évidence :** [le bandeau « Exploration des données » et]{.nouveau} les tuiles « Mes plans de gestion » et « Mes sites ».

## 1.3 L'en-tête : notifications et menu

En haut de chaque page, vous trouvez :

- [**Le bouton de menu** (à gauche) : il ouvre le menu latéral (Accueil, Plans de gestion, Sites,
  Mes inventaires et suivis, Exploration des données…). Si votre structure a défini un logo, il
  s'affiche à côté.]{.nouveau}
- **La cloche de notifications** : [un compteur indique le nombre de **notifications non lues**.
  Si vous avez des demandes de validation à traiter, elles sont signalées à part, par une petite
  pastille rouge et un encart « Validations en attente » dans la liste.]{.nouveau} En cliquant sur
  la cloche, vous voyez vos dernières notifications et pouvez tout marquer comme lu[ ; le lien
  « Voir toute l'activité » ouvre la page Activité]{.nouveau}.
- **Le menu utilisateur** (votre nom, en haut à droite) : il donne accès à *Mon profil*,
  *Mes demandes* et à la *Déconnexion*.

> 📸 **Capture 5 — Cloche de notifications et menu utilisateur** \
> **Écran :** en-tête de l'application, cloche de notifications ouverte (liste de messages) et menu utilisateur déroulé. \
> **État à reproduire :** au moins une notification non lue (badge visible sur la cloche). \
> **À mettre en évidence :** le badge de la cloche et les entrées du menu utilisateur.

## 1.4 Mon profil

La page **Mon profil** regroupe :

- **Vos informations personnelles** : nom, e-mail, rôle, identifiant, date d'inscription,
  dernière connexion. [Si votre identifiant n'est pas renseigné, un lien **« Définir un
  identifiant »** vous permet de le créer : vous pourrez ensuite vous connecter avec lui en plus
  de votre e-mail.]{.nouveau}
- **Votre organisme** : nom et coordonnées.
- **La gestion de votre compte** : vous pouvez demander la **suppression de votre compte**
  (conformément au RGPD). La suppression devient définitive après un délai ; tant que ce délai
  n'est pas écoulé, vous pouvez **annuler** votre demande.

> 📸 **Capture 6 — Page Mon profil** \
> **Écran :** page de profil avec les blocs informations personnelles, organisme et gestion du compte. \
> **À mettre en évidence :** le bloc « Gestion de mon compte » (demande de suppression).

## 1.5 Les notifications

CICADA vous informe des événements qui vous concernent (validation d'une demande, ajout à un site,
etc.). [Vos notifications se consultent depuis la cloche de l'en-tête ; l'historique complet est
disponible sur la page Activité.]{.nouveau} Vous pouvez marquer un message comme lu, ou tout
marquer comme lu d'un seul clic.

## 1.6 La page Activité

La page **Activité** retrace, sous forme de fil chronologique, ce qui s'est passé sur votre
périmètre. Des onglets vous permettent de filtrer :

- **Tout** : l'ensemble de l'activité visible ;
- **Mes sites** : ce qui concerne vos sites ;
- **Mes plans** : ce qui concerne vos plans ;
- **Mes droits** : l'historique de vos accès (ajouts, retraits, validations).

[Les administrateurs disposent d'onglets supplémentaires (Validations, et pour le super
administrateur : Système et RGPD).]{.nouveau}

Une barre de recherche et des filtres aident à retrouver une action précise.

> 📸 **Capture 7 — Page Activité** \
> **Écran :** fil d'activité avec les onglets en haut et plusieurs entrées groupées par date. \
> **À mettre en évidence :** la barre d'onglets et une entrée du fil (avec son icône d'action).

## 1.7 Mes demandes

La page **Mes demandes** vous permet de suivre toutes vos demandes : accès à un site, à un plan,
à un module, ou inscription. Pour chaque demande, vous voyez son **type**, sa **cible**, sa
**date** et son **statut** (en attente, approuvée, refusée). Vous pouvez **annuler** une demande
encore en attente.

::: nouveau
Tant qu'une demande est en attente, la colonne **« Traité par »** affiche le nom des personnes
qui peuvent la valider (le survol d'un nom indique son rôle et son organisme). Si une demande a été
refusée avec un commentaire, une icône d'information permet de le lire.
:::

Cette page liste aussi les **modules** auxquels vous n'avez pas encore accès : un bouton
**Demander l'accès** ouvre une fenêtre où vous justifiez votre demande.

> 📸 **Capture 8 — Page Mes demandes** \
> **Écran :** page « Mes demandes » avec les compteurs (en attente / approuvées / refusées) et le tableau de l'historique. \
> **À mettre en évidence :** les compteurs en haut, la colonne « Statut » [et la colonne « Traité par » d'une demande en attente]{.nouveau}.

## 1.8 Consulter les sites

Le module **Sites** [(« Mes sites »)]{.nouveau} présente une **carte** (à gauche) et un
**tableau** (à droite). Cliquez sur un site dans le tableau pour le localiser sur la carte, et
inversement.

Vous voyez par défaut **vos sites** [; la colonne « Statut » indique si vous en êtes
**Référent** ou si vous y avez simplement **Accès**]{.nouveau}. La **fiche d'un site** détaille
ses informations générales, les organismes gestionnaires, les utilisateurs rattachés et les plans
de gestion associés.

Si un site qui vous intéresse n'apparaît pas, utilisez **[Rechercher ou créer]{.nouveau}** :

- si le site existe déjà [dans votre organisme]{.nouveau} mais que vous n'y avez pas accès, vous
  pouvez **demander l'accès** [(simple ou « Comme référent »)]{.nouveau} ;
- si le site appartient à un autre organisme, vous pouvez **demander le rattachement** de votre
  organisme [(« Demander à lier à mon organisme »), en demandant éventuellement l'accès en même
  temps]{.nouveau} ;
- si aucun site ne correspond, vous pouvez **créer un nouveau site** [: tracez son contour sur la
  carte (ou importez un fichier) et renseignez son nom, son type, sa surface, ses identifiants
  local et INPN. Avant l'envoi, CICADA vous indique si le site sera validé automatiquement ou qui
  sera notifié pour le valider]{.nouveau}.

Vous pouvez également **demander à devenir référent** d'un site auquel vous avez accès [(bouton
« Devenir référent » sur la fiche du site)]{.nouveau}.

::: nouveau
**Un site que vous avez créé est en attente de validation ?** Il apparaît dans le bloc « Sites en
attente de validation ». Vous pouvez :

- le **Modifier** pour le compléter ou le corriger avant sa validation ;
- **Annuler la demande** : le site en attente est alors supprimé (une confirmation vous est
  demandée).
:::

> 📸 **Capture 9 — Module Sites (carte + tableau)** \
> **Écran :** module Sites avec la carte à gauche et le tableau des sites à droite. \
> **À mettre en évidence :** le bouton « [Rechercher ou créer]{.nouveau} » [et le bloc « Sites en attente de validation » avec ses boutons Modifier / Annuler la demande]{.nouveau}.

> 📸 **Capture 10 — Fenêtre [« Rechercher un site ou en créer un nouveau »]{.nouveau}** \
> **Écran :** fenêtre de recherche avec les résultats séparés entre « Sites de mon organisme » et « Sites d'autres organismes ». \
> **À mettre en évidence :** les boutons « Demander l'accès », « Comme référent » et « Demander à lier à mon organisme ».

> 💡 **Cas d'usage — Mon site n'a pas de code INPN / n'est pas trouvé** \
> **Situation :** lors de la recherche ou de la création d'un site, je ne trouve pas mon site et je n'ai pas de code INPN à renseigner. \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

## 1.9 Consulter les plans de gestion

Le module **Plans de gestion** liste les plans auxquels vous avez accès. Vous pouvez rechercher et
trier [par nom, période de validité ou statut, et **filtrer par statut** (Brouillon, Validé,
Modifié, Terminé — par défaut, les plans terminés sont masqués). Le bouton **« Voir les anciennes
versions »** affiche toute la chaîne des versions d'un plan]{.nouveau}. En cliquant sur **Voir**,
vous ouvrez sa **fiche détaillée**. [Pour les référents, le bouton **« Suivre »** ouvre
directement le suivi d'un plan validé.]{.nouveau}

::: nouveau
En tant qu'utilisateur lié à un plan (membre du plan, rattaché à l'un de ses sites, ou membre d'un
organisme rédacteur ou gestionnaire), vous consultez **tout le contenu du plan en lecture seule** :

- la **Vue d'ensemble** (synthèse, sites, utilisateurs, documents à télécharger) ;
- **Détails et saisie** : les enjeux, facteurs clés de réussite, objectifs, indicateurs et
  actions, ainsi que les **fiches action** ;
- le **Tableau d'arborescence**.

Un bandeau vous rappelle que vous n'êtes pas référent du plan ; il propose un bouton
**« Demander à devenir référent »**. Les **suivis** (tableau de bord, suivi des actions, bilan) et
les **exports** sont réservés aux référents du plan et aux administrateurs.
:::

[**Vous n'avez pas accès à un plan ?** En bas de la liste, la section « Demander l'accès à un
plan » permet de rechercher un plan et d'en demander l'accès (ou, si vous n'êtes pas rattaché à
son site, le lien et l'accès). Les demandes en cours apparaissent dans « Plans en attente de
validation ».]{.nouveau}

> 📸 **Capture 11 — Fiche d'un plan en consultation** \
> **Écran :** fiche d'un plan de gestion ouverte sur la vue d'ensemble, par un utilisateur non référent. \
> **À mettre en évidence :** le menu de navigation interne du plan (Vue d'ensemble, Détails et saisie, Tableau d'arborescence) [et le bandeau « Vous n'êtes pas référent de ce plan de gestion »]{.nouveau}.

::: nouveau
## 1.10 Explorer les données des plans de gestion

Le module **Exploration des données** (bandeau de l'accueil ou menu latéral) permet de rechercher
dans les plans de gestion **validés** — les brouillons n'apparaissent jamais. Il est ouvert à tout
utilisateur connecté.

**Portée de la recherche.** Un message indique, avant toute recherche, sur quels plans elle
porte :

- si votre structure **partage** ses plans avec l'exploration nationale : les plans de **toutes
  les structures participantes** ;
- sinon : **uniquement les plans de votre instance**.

**Deux modes de recherche :**

- **« Un contenu d'un plan de gestion »** : retrouver les enjeux, facteurs d'influence, pressions,
  objectifs, indicateurs, actions ou suivis qui partagent un mot-clé (ex. « limicole »,
  « fréquentation »). Un menu « Type de données » restreint la recherche à un type d'élément.
- **« Un plan de gestion »** : retrouver les plans d'un site, d'un département, d'une région, ou
  par leur nom.

**Les résultats** peuvent être triés (pertinence, ordre alphabétique, plus récents) et filtrés :
zone géographique, structure d'origine, organismes gestionnaires, types d'aires protégées, statut,
et, pour les contenus, catégorie d'enjeu, type d'indicateur, objectifs et actions de gestion.
L'option **« Rechercher dans les titres uniquement »** peut être désactivée pour élargir la
recherche aux descriptions, aux éléments parents et aux espèces, habitats ou protocoles
rattachés.

Chaque résultat indique :

- **pourquoi il répond** à la recherche lorsque le mot n'est pas dans son titre (« Trouvé via une
  espèce, un habitat ou un protocole rattaché », « Trouvé dans la description »…) ;
- le plan, le gestionnaire principal, les sites et la période ;
- en exploration nationale, la **structure d'origine** (pastille avec un globe).

CICADA **tolère les fautes de frappe** : si aucun résultat ne correspond exactement, il propose
les contenus dont un mot s'approche le plus.

**La fiche publique d'un plan** présente, en lecture seule, sa vue d'ensemble, ses enjeux (avec
facteurs, pressions et objectifs) et ses actions (avec leur fiche). Elle indique quelle structure
l'a publiée et à quelle date. **Le budget, les moyens humains, les mesures d'indicateurs et le
suivi des réalisations ne sont jamais partagés.**

> 📸 **Capture 12 — Exploration des données : page de recherche** \
> **Écran :** page « Exploration des données des plans de gestion » en mode « Un contenu d'un plan de gestion ». \
> **À mettre en évidence :** le message de portée, le choix du mode de recherche et le champ « Mot-clé ».

> 📸 **Capture 13 — Exploration des données : résultats** \
> **Écran :** liste de résultats d'une recherche de contenu, avec le panneau « Filtrer les résultats ». \
> **État à reproduire :** un résultat trouvé via une espèce rattachée ; en exploration nationale si possible. \
> **À mettre en évidence :** la mention « Trouvé via… », la pastille de structure d'origine et le panneau de filtres.

> 💡 **Cas d'usage — Comparer mes indicateurs avec ceux d'autres gestionnaires** \
> **Situation :** je rédige un indicateur et je voudrais voir comment d'autres gestionnaires suivent le même enjeu (même espèce, même habitat). \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_
:::

---
---

# Partie 2 — Notice Administrateur de plan de gestion

> **À qui s'adresse cette notice ?**
> Aux personnes chargées de **saisir et de suivre un plan de gestion** (les référents du plan).
> Elle complète la Partie 1 : pensez à lire d'abord la **Partie 1** pour les fonctions de base
> (connexion, profil, consultation).
>
> **Ce que vous pouvez faire en plus :**
> - créer un plan et en saisir tout le contenu (enjeux, objectifs, actions, indicateurs)[, y
>   compris en l'**important depuis un fichier Excel**]{.nouveau} ;
> - gérer le cycle de vie du plan (brouillon, validation, [fin]{.nouveau}, révision…) ;
> - [décrire les postes (ressources humaines) du plan ;]{.nouveau}
> - renseigner le suivi (réalisation des actions, indicateurs, bilan) ;
> - joindre des documents au plan[ ;]{.nouveau}
> - [exporter le plan (Word, Excel).]{.nouveau}

> ℹ️ **Voir la Partie 1** pour : se connecter, gérer son profil, consulter sites et plans, demander un accès.

[En tant que référent, vous avez aussi accès à l'espace **Administration** (lien dans l'en-tête),
limité aux pages **Validations**, **Sites** et **Plans de gestion** : vous y traitez notamment les
demandes d'accès à vos plans et à vos sites (voir Partie 3, « Traiter les validations »).]{.nouveau}

## 2.1 Créer un plan de gestion

Depuis le module **Plans de gestion**, cliquez sur **[Créer un plan de gestion]{.nouveau}**[, puis
choisissez :]{.nouveau}

- [**« À partir d'une base vierge »** : nouveau plan créé depuis le début ;]{.nouveau}
- [**« Sur la base d'un PG existant »** : un plan existant sert de modèle ; vous choisissez ce
  qui est repris (sites associés, référents, fichiers joints, enjeux et FCR, sous-éléments).]{.nouveau}

Le formulaire [« Saisie des informations générales »]{.nouveau} vous demande :

- le **nom** du plan, ses **années de début et de fin**, son **rang** [(n-ième plan de gestion du
  site : 1er PG = rang 1… à ne pas confondre avec la version)]{.nouveau} [et s'il a été rédigé
  selon la **méthode CT88**]{.nouveau} ;
- des informations facultatives : surface, [date de l'avis du CSRPN,]{.nouveau} type et organisme
  rédacteur principal [(un organisme absent peut être créé)]{.nouveau}, noms des rédacteurs,
  relecteurs et autres contributeurs ;
- les **sites** couverts par le plan (vous pouvez en sélectionner plusieurs). [Si votre site
  n'est pas dans la liste, il faut d'abord le créer (voir Partie 1, « Consulter les
  sites »).]{.nouveau}

::: nouveau
**Le fil entre les rangs.** Lorsque les sites choisis ont déjà des plans de gestion, un encadré
s'affiche :

- un **avertissement** (non bloquant) si un plan du même rang existe déjà sur le site ;
- la case **« Rattacher ce plan à la suite de … »**, cochée par défaut : elle relie le nouveau
  plan au plan du rang précédent, pour conserver l'historique du site. Décochez-la pour créer un
  plan indépendant ;
- le volet **« Plans de gestion déjà associés à ce site »**, qui les liste par rang.
:::

À l'enregistrement, le plan est créé en **brouillon** : il est alors entièrement modifiable.
[Vous en devenez automatiquement **référent**. Tant que le plan est en brouillon, le bouton
**« Modifier le plan de gestion »** permet de revenir sur ces informations générales (y compris
le lien avec le plan du rang précédent) ; la fenêtre rappelle la place du plan dans sa chaîne de
versions (rang, version, plan parent).]{.nouveau}

> 📸 **Capture [14]{.nouveau} — Formulaire de création d'un plan** \
> **Écran :** formulaire « Saisie des informations générales », avec la section de sélection des sites. \
> **État à reproduire :** un site qui possède déjà un plan de rang 1, et le rang 2 saisi. \
> **À mettre en évidence :** les champs nom / années / rang, la section « Choix des sites » [et la case « Rattacher ce plan à la suite de … »]{.nouveau}.

> 💡 **Cas d'usage — Mon plan existant a déjà été validé ou évalué** \
> **Situation :** je saisis un plan rédigé il y a plusieurs années, déjà validé (voire déjà évalué à mi-parcours). Quel statut lui donner et comment retracer son historique ? \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

::: nouveau
> 💡 **Cas d'usage — Les plans des rangs précédents ne sont pas dans CICADA** \
> **Situation :** je saisis le 3e plan de gestion de mon site, mais les plans de rang 1 et 2 n'ont jamais été saisis. Dois-je les créer pour conserver le fil entre les rangs ? \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_
:::

## 2.2 La fiche du plan et sa navigation

La fiche d'un plan s'organise autour d'une **barre latérale** :

- [**Paramétrage** : les **Paramètres** du plan (import, suppression de version) et les
  **Postes / RH** ;]{.nouveau}
- **Vue d'ensemble** : la synthèse du plan (enjeux, objectifs, actions, documents) ;
- **Détails et saisie** : [la liste des enjeux et des facteurs clés de réussite (FCR)]{.nouveau} et
  leur contenu ;
- **Suivis** : bilan, suivi des actions, tableau de bord ;
- **Tableau d'arborescence** : une vue cartographiée de tout le plan[ ;]{.nouveau}
- [**Exports** : les documents Word et Excel du plan.]{.nouveau}

[Les rubriques Paramétrage, Suivis et Exports ne sont visibles que des référents du plan et des
administrateurs.]{.nouveau}

La **vue d'ensemble** affiche les informations clés (période, organisme, statut, surface) et des
sections dépliables : synthèse des enjeux, des objectifs long terme, des objectifs opérationnels,
des actions, des suivis, ainsi que [les sites, les utilisateurs (référents et membres)]{.nouveau}
et les documents joints.

> 📸 **Capture [15]{.nouveau} — Vue d'ensemble d'un plan + barre latérale** \
> **Écran :** fiche d'un plan en vue d'ensemble, barre latérale visible à gauche. \
> **À mettre en évidence :** la barre latérale [(avec Paramétrage et Exports)]{.nouveau} et le bandeau de statut du plan.

::: nouveau
## 2.3 Le paramétrage du plan

### Les postes (ressources humaines)

La page **Postes / RH** décrit les **types de postes** qui travaillent sur le plan : leur
fonction, le nombre de personnes et leur organisme. **Aucune donnée nominative n'est
enregistrée** (RGPD) : un poste est décrit par sa fonction, pas par la personne qui l'occupe.

Cliquez sur **« Ajouter un type de poste »** puis :

- choisissez la **fonction** (si elle manque, « ajouter une nouvelle fonction » : elle ne sera
  proposée que dans ce plan) ; chaque fonction a un type : salarié, stagiaire, bénévole ou
  partenaire ;
- indiquez le **nombre de personnes** ;
- pour les salariés et stagiaires : l'**organisme** et le **coût jour** de chaque personne ; pour
  les bénévoles : un coût jour (0 si non valorisé) ; pour un prestataire ou un partenaire :
  l'organisme en texte libre ;
- facultatif : un **nom local du poste** (ex. « garde du secteur nord »), qui remplace la fonction
  dans les fiches action, et un **commentaire** (sans nom ni prénom).

Ces postes alimentent ensuite le **temps de travail** des actions et le calcul automatique du
**coût salarial** (jours × coût jour).

> 📸 **Capture 16 — Page Postes / RH et fenêtre d'ajout d'un poste** \
> **Écran :** page « Postes / Ressources humaines » avec quelques postes, et la fenêtre « Ajouter un type de poste » ouverte. \
> **À mettre en évidence :** le rappel RGPD, le champ « Coût jour » et le « Nom local du poste ».

> 💡 **Cas d'usage — Mon plan d'origine exprimait les moyens humains en ETP ou par personne nommée** \
> **Situation :** mon plan historique indique les moyens humains en ETP, ou avec le nom des agents. Comment les traduire en postes et en jours ? \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

### Importer un plan depuis un fichier Excel

Pour reprendre un plan existant sans tout ressaisir à la main, la page **Paramètres** propose deux
imports. **L'import n'est possible que sur un plan en brouillon.**

**Import de l'arborescence** (enjeux, facteurs, pressions, objectifs, indicateurs, métriques) :

1. **Partir d'un modèle** : téléchargez le **modèle à remplir** (chaque onglet contient une ligne
   « (exemple) » grisée, jamais importée) ou un **exemple complet** pour vous inspirer.
2. **Remplir le fichier dans Excel** : les onglets sont reliés par des **codes** (E1, F1…) et des
   **listes déroulantes** vous guident.
3. **Importer votre fichier** : CICADA vérifie le fichier et affiche soit « Fichier valide » avec le
   nombre d'éléments qui seront créés, soit la liste des **anomalies** (onglet, ligne, colonne).

Si le plan contient déjà une arborescence, vous choisissez d'**ajouter** le contenu du fichier à
l'existant ou de **remplacer** tout le contenu (action irréversible, une confirmation est
demandée).

**Corriger sans repasser par Excel :** le bouton **« Corriger dans un tableau »** affiche le
contenu du fichier à l'écran, cellules en erreur en rouge. Corrigez-les directement, cliquez sur
**« Revalider »**, puis **« Importer »**.

**Import des actions** : même principe, avec le **classeur des actions** (actions, lignes de
budget et de ressources humaines).

> 📸 **Capture 17 — Import de l'arborescence : correction dans un tableau** \
> **Écran :** page Paramètres, import de l'arborescence avec le tableau de correction ouvert. \
> **État à reproduire :** un fichier contenant deux ou trois erreurs. \
> **À mettre en évidence :** les cellules en rouge, le compteur d'erreurs et le bouton « Revalider ».

> 💡 **Cas d'usage — Mon plan d'origine est dans un tableur qui ne suit pas le modèle** \
> **Situation :** mon plan existant est déjà dans un fichier Excel, mais avec une organisation différente du modèle CICADA. \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

### Supprimer une version

La page **Paramètres** permet aussi de **supprimer la version affichée** du plan : son contenu
(enjeux, actions, suivis, fichiers) et ses liens sont définitivement effacés, et les versions
restantes sont renumérotées. Supprimer la version d'évaluation à mi-parcours annule cette
évaluation. **Cette action est irréversible.**
:::

## 2.4 Le cycle de vie du plan

Un plan passe par plusieurs **statuts** :

| Statut | Signification |
|--------|---------------|
| **Brouillon** | En cours de saisie. **C'est le seul statut où le contenu est modifiable.** |
| **Validé** | Plan approuvé. Le contenu passe en lecture seule. |
| **Modifié** | Plan validé puis modifié au sein du même cycle. |
| **[Terminé]{.nouveau}** | Plan clôturé, conservé pour l'historique[ : il reste consultable, mais le suivi n'est plus accessible]{.nouveau}. |

[Des **étiquettes** peuvent s'ajouter au statut : « En cours de révision », « Évaluation
mi-parcours », et pour un plan prolongé « Prolongé » (réserves naturelles), « En renouvellement »
(parcs naturels régionaux) ou « Étendu ».]{.nouveau}

Lorsqu'un plan **n'est pas en brouillon**, un **bandeau de verrouillage** s'affiche en haut de la
page : le contenu ne peut plus être modifié. Pour le retravailler, il faut le repasser en brouillon
ou créer une nouvelle version.

Selon le statut et vos droits, vous disposez d'**actions de cycle de vie** :

- **Valider le plan** (depuis un brouillon) [; si un plan précédent de la chaîne est encore
  actif, CICADA propose de le **terminer**]{.nouveau} ;
- [**Modifier ce plan de gestion** (sur un plan validé) : une fenêtre vous recommande de **créer
  une nouvelle version** (le contenu est copié dans un nouveau brouillon, la version validée reste
  intacte) plutôt que de **remettre cette version en brouillon** (la validation est alors annulée
  et le suivi n'est plus accessible) ;]{.nouveau}
- **Étendre la durée du plan** (+1 ou +2 ans, 2 ans au maximum au total) [: CICADA crée un
  **brouillon de version étendue**, à compléter (actions et suivi des années ajoutées) puis à
  valider]{.nouveau} / **Annuler l'extension** ;
- [**Marquer en cours de révision**]{.nouveau} / [**Annuler la révision**]{.nouveau} [: au
  lancement, vous pouvez créer le brouillon du plan du rang suivant, le lier à un brouillon
  existant, ou marquer le plan sans lien]{.nouveau} ;
- **[Lancer les modifications après l'évaluation mi-parcours]{.nouveau}** [: crée (ou lie) un
  brouillon, marqué « évaluation mi-parcours » dès sa création ; une seule évaluation mi-parcours
  est possible par plan]{.nouveau} ;
- **[Terminer]{.nouveau}** / **Réactiver** le plan.

::: nouveau
**Les validations administratives** (avis du CSRPN, validation par le comité consultatif, arrêté
préfectoral pour les réserves naturelles nationales) ne concernent que les **réserves naturelles**
(RNN, RNR, RNC). Pour ces plans, un badge **« Validations administratives »** s'affiche à côté du
statut : cliquez dessus pour **enregistrer, modifier ou effacer** chaque validation (date, et
numéro pour l'arrêté). Ces validations ne bloquent pas le changement de statut du plan.
:::

Une **chronologie des versions** [(encadré « Cycle de vie »)]{.nouveau} retrace l'historique du
plan et de ses révisions[, regroupées par rang ; un clic sur une version l'ouvre]{.nouveau}.

> 📸 **Capture [18]{.nouveau} — Actions de cycle de vie + bandeau de verrouillage** \
> **Écran :** fiche d'un plan validé, avec le bandeau « Plan verrouillé en lecture seule » et les boutons d'actions de cycle de vie. \
> **État à reproduire :** un plan au statut « Validé » [sur une réserve naturelle]{.nouveau}. \
> **À mettre en évidence :** le bandeau de verrouillage, les boutons (Modifier ce plan de gestion, Terminer…) [et le badge « Validations administratives »]{.nouveau}.

::: nouveau
> 📸 **Capture 19 — Fenêtre « Modifier ce plan validé »** \
> **Écran :** fenêtre ouverte par « Modifier ce plan de gestion » sur un plan validé. \
> **À mettre en évidence :** l'option recommandée « Créer une nouvelle version » et l'option « Remettre cette version en brouillon ».
:::

> ⚠️ **Important — Qui peut gérer le cycle de vie ?**
> Les actions de cycle de vie sont réservées aux **référents du plan** et aux administrateurs.
> Les autres utilisateurs consultent le plan sans pouvoir changer son statut.

## 2.5 Les enjeux et leur contenu

Le cœur de la saisie se fait dans **Détails et saisie**. Pour chaque **enjeu** (ou facteur clé de
réussite), vous renseignez son intitulé[, un intitulé court, sa priorité (1, 2, 3 ou « Non
définie ») et sa catégorie]{.nouveau}.

::: nouveau
Pour un **enjeu de conservation du patrimoine naturel**, vous indiquez à quoi il est lié :
habitats, espèces, patrimoine géologique, fonctionnalités des écosystèmes ou autre.

- **Habitats et espèces** : au moins un élément est alors obligatoire. La recherche d'espèces
  s'appuie sur TaxRef ; si votre taxon n'est pas trouvé, le lien **« Je ne trouve pas mon taxon
  (rechercher dans les synonymes) »** élargit la recherche aux synonymes et rattache le nom valide.
  La recherche d'habitats s'appuie sur HabRef et peut être **filtrée par typologie**. Une liste de
  codes peut aussi être **importée** d'un coup.
- **Patrimoine géologique** : choisissez le site dans l'inventaire du patrimoine géologique, le
  type de patrimoine (in situ, ex situ, documents, autre) et les **objets géologiques** concernés
  dans des listes déroulantes. Le type « Documents » permet de joindre des fichiers ou d'ajouter
  une référence à un document papier.

Pour un **enjeu socio-économique**, vous indiquez s'il est lié à la valeur paysagère, au
patrimoine culturel, aux ressources, aux usages, etc.

Un **facteur clé de réussite (FCR)** a sa propre catégorie (connaissance, ancrage territorial,
fonctionnement de l'aire protégée, surveillance, autre) ; il n'a pas besoin de pression préalable.

**Numéroter à la main.** Les enjeux, FCR, objectifs à long terme et objectifs opérationnels sont
numérotés automatiquement. Le champ **« Numéro fixé (facultatif) »** permet d'imposer un numéro
(pour reprendre la numérotation de votre plan d'origine) : il ne bougera plus et les autres
éléments sauteront ce numéro.
:::

Chaque enjeu se décline ensuite selon trois onglets :

- **[Détail enjeu]{.nouveau}** : les **facteurs d'influence** et les **pressions** qui pèsent sur
  l'enjeu [(le type de pression peut être choisi dans le référentiel PressRef)]{.nouveau} ;
- **[Vision à long terme]{.nouveau}** : la hiérarchie
  **Objectif long terme → Niveau d'exigence → Indicateur d'état → Métrique**, puis les actions ;
- **[Stratégie opérationnelle]{.nouveau}** : [les **objectifs opérationnels** (associés à une ou
  plusieurs pressions), les **résultats attendus**, les **indicateurs de pression** et leurs
  actions.]{.nouveau}

[Un rappel de l'**ordre de saisie** figure en haut de chaque onglet.]{.nouveau}

::: nouveau
**Les boutons « Je n'ai pas de … ».** Lorsqu'un niveau de la hiérarchie n'existe pas dans votre
plan, un bouton permet de créer un élément **« Non défini »** qui tient la place, sans inventer de
contenu. Il est préconisé de le renseigner dès que possible. Six boutons existent :

- « Je n'ai pas de facteur d'influence » ;
- « Je n'ai pas de pression » ;
- « Je n'ai pas de niveau d'exigence » ;
- « Je n'ai pas d'indicateur d'état » ;
- « Je n'ai pas de résultat attendu » ;
- « Je n'ai pas d'indicateur de pression ».

**Réorganiser par glisser-déposer.** Les facteurs d'influence se réordonnent par glisser-déposer ;
une pression peut être déplacée vers un autre facteur, et une action vers un autre indicateur.
:::

> 📸 **Capture [20]{.nouveau} — Détail d'un enjeu (les trois onglets)** \
> **Écran :** détail d'un enjeu, montrant les onglets « Détail enjeu », « Vision à long terme » et « Stratégie opérationnelle ». \
> **À mettre en évidence :** la barre des trois onglets, la hiérarchie des objectifs [et un bouton « Je n'ai pas de … »]{.nouveau}.

> 💡 **Cas d'usage — L'habitat de mon enjeu n'existe pas dans HabRef** \
> **Situation :** au moment de saisir un enjeu, l'habitat que je veux associer n'est pas trouvé dans le référentiel HabRef. \
> [**Ce que propose CICADA :** filtrer par typologie ; à défaut, le lien « Je ne trouve pas mon habitat dans la liste » permet de saisir librement un habitat hors référentiel (sans code).]{.nouveau} \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

> 💡 **Cas d'usage — Mon enjeu ne cible ni un habitat ni un taxon précis** \
> **Situation :** mon enjeu porte sur un thème transversal (paysage, fréquentation…) sans habitat ni espèce identifiable. \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

::: nouveau
> 💡 **Cas d'usage — Mon plan d'origine saute un niveau (pas de niveau d'exigence, pas de résultat attendu…)** \
> **Situation :** mon plan historique relie directement un objectif à un indicateur, sans niveau d'exigence (ou sans résultat attendu). \
> **Ce que propose CICADA :** les boutons « Je n'ai pas de … » créent un élément « Non défini » à ce niveau. \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

> 💡 **Cas d'usage — Mon plan d'origine n'avait pas de priorité ou avait une autre numérotation** \
> **Situation :** mes enjeux n'étaient pas priorisés, ou leur numérotation ne suit pas l'ordre de saisie. \
> **Ce que propose CICADA :** priorité « Non définie » et « Numéro fixé (facultatif) ». \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_
:::

::: nouveau
## 2.6 Lier ou copier un élément

Un même élément peut concerner plusieurs parties du plan (un facteur d'influence commun à deux
enjeux, une action qui répond à plusieurs indicateurs…). Plutôt que de le saisir deux fois, les
boutons de partage proposent deux choix :

- **Lier** : l'élément reste **unique** et s'affiche à plusieurs endroits. Toute modification se
  répercute partout. Un badge (« Lié à plusieurs enjeux », « Liée à plusieurs métriques »…) le
  signale.
- **Copier** : crée un **duplicata indépendant** (avec tout son contenu), modifiable séparément.

Sont concernés : les facteurs d'influence, les objectifs opérationnels, les résultats attendus, les
actions et les indicateurs (pour un indicateur, la copie se fait par « Dupliquer cet
indicateur »). Un élément lié peut être **retiré d'un emplacement** (« Retirer d'ici ») sans être
supprimé des autres ; il ne peut pas être retiré de l'endroit où il a été créé.

Depuis un indicateur, **« Ajouter une action »** propose de créer une nouvelle action, de **lier**
une action existante ou d'en **copier** une.

> 📸 **Capture 21 — Fenêtre « Partager ou copier »** \
> **Écran :** fenêtre de partage d'un facteur d'influence, avec les cartes « Lier » et « Copier ». \
> **À mettre en évidence :** les deux cartes et l'explication de chacune.

> 💡 **Cas d'usage — Une même action répond à plusieurs objectifs de mon plan** \
> **Situation :** dans mon plan d'origine, une action est citée sous plusieurs objectifs ou enjeux. Faut-il la lier ou la copier ? \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_
:::

## 2.7 Les indicateurs et les métriques

Sous chaque niveau d'exigence, vous définissez des **indicateurs d'état** [; sous chaque résultat
attendu, des **indicateurs de pression** ; les **indicateurs de réponse** se saisissent dans
l'action]{.nouveau}. Chaque indicateur porte une ou plusieurs **métriques** : c'est la mesure
concrète qui sera suivie dans le temps.

::: nouveau
Une métrique comporte : un **intitulé**, une **unité**, une **pondération**, un **état de
référence** et un **type de grille** (obligatoire), qui définit comment une valeur mesurée est
convertie en score de 1 (très mauvais) à 5 (très bon) :

| Type de grille | Principe |
|----------------|----------|
| **Intervalle numérique** | Des valeurs limites séparent les niveaux. Vous choisissez le **sens** (croissant ou décroissant) et, pour chaque limite, à quel niveau elle appartient (borne incluse ou exclue). |
| **Chiffre** | Une valeur chiffrée par niveau. |
| **Texte** | Un libellé par niveau (ex. « absent », « présent », « abondant »). |
| **Indéterminé** | La grille sera définie plus tard, une fois le type de mesure précisé. |

Pour les grilles Chiffre et Texte, vous pouvez **désactiver** les niveaux inutiles (« Non
utilisé »).

**Métriques à plusieurs blocs.** Avec une grille « Intervalle numérique », le bouton **« Ajouter un
bloc »** permet de combiner plusieurs mesures (ex. hauteur ET densité). Chaque bloc a son
intitulé, son unité et sa grille ; les blocs sont reliés par **ET** (on retient le moins bon score)
ou **OU** (on retient le meilleur), avec des parenthèses si besoin.
:::

> 📸 **Capture 22 — Édition d'une métrique** [(nouvelle capture)]{.nouveau} \
> **Écran :** formulaire d'une métrique « Intervalle numérique » à deux blocs. \
> **À mettre en évidence :** le sens de variation, le choix « inclu dans » d'une limite et la formule ET / OU.

> 💡 **Cas d'usage — Mon plan d'origine indiquait une unité pour la métrique** \
> **Situation :** dans mon plan rédigé auparavant, la métrique était exprimée avec une unité (nombre, surface, pourcentage…). Où et comment renseigner cette unité dans CICADA ? \
> [**Ce que propose CICADA :** un champ « Unité » sur la métrique, et un par bloc pour une métrique à plusieurs blocs.]{.nouveau} \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

> 💡 **Cas d'usage — Ma métrique n'a pas de valeur cible chiffrée** \
> **Situation :** l'indicateur de mon plan est qualitatif (présence/absence, dire d'expert…) et n'a pas de cible chiffrée. \
> [**Ce que propose CICADA :** grille « Texte », ou « Indéterminé » en attendant.]{.nouveau} \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

::: nouveau
> 💡 **Cas d'usage — Mon plan d'origine n'avait que 3 classes d'état (et non 5)** \
> **Situation :** mon indicateur historique classait l'état en « bon / moyen / mauvais ». \
> **Ce que propose CICADA :** désactiver les niveaux inutilisés. \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_
:::

## 2.8 Les actions (opérations)

Une **action** se saisit via son formulaire dédié. Vous y renseignez notamment :

- le **type d'action** [(obligatoire)]{.nouveau} choisi dans une liste organisée par catégorie
  [; et facultativement la catégorie d'action réserve (domaines d'activité CT88)]{.nouveau} ;
- [le **code de l'action**, calculé automatiquement (ex. CS1) et affiché en direct ; le champ
  « Numéro fixé » permet d'imposer son numéro ;]{.nouveau}
- l'**intitulé** [(rempli automatiquement avec le type d'action s'il reste vide)]{.nouveau}, les
  [**métriques associées** et la **priorité**]{.nouveau} ;
- [pour une action d'inventaire ou de suivi (type CS) : les **détails de l'inventaire ou du suivi**
  (objectif, cible, taxons ou habitats référés), le **protocole** et la **bancarisation** de la
  donnée ;]{.nouveau}
- la **programmation** : [sites concernés, années, **temps de travail**, **budget** et mois
  prévus ; opérateurs, partenaires et financeurs]{.nouveau} ;
- la **localisation** (emprise spatiale) [— une case permet de reprendre l'emprise du ou des
  sites]{.nouveau} ;
- les **indicateurs de réponse** [: un intitulé (obligatoire), puis soit une métrique simple avec
  une valeur cible, soit une **grille de scoring à 5 niveaux** (case « Utiliser une grille de
  scoring »), construite comme celle des métriques (voir 2.7)]{.nouveau}.

::: nouveau
**Le protocole (actions de suivi).** Indiquez si le protocole est **standardisé** :

- **oui** : recherchez-le dans le catalogue des protocoles standardisés (dont les 5 protocoles
  **MhéO** pour les zones humides), consultez sa fiche, puis précisez si vous le **respectez
  strictement** (sinon, pourquoi et avec quelles différences) ;
- **non** : décrivez votre protocole (nom, ETP par cycle, description, objectif, période
  d'échantillonnage).

La **fréquence** (ex. 2 fois par an) peut être appliquée automatiquement aux années et aux mois
avec le bouton « Appliquer aux années ».

**Le mode de ventilation du budget.** Il définit le niveau de détail de la programmation :

| Mode de ventilation | Ce que vous saisissez |
|---------------------|------------------------|
| Pas de ventilation | Un budget et un temps de travail globaux par année |
| Par organisme | Le budget et le temps réparti entre les organismes gestionnaires |
| Par type de budget | Fonctionnement / investissement |
| Par organisme + type de budget | Les deux combinés |
| Par type de budget + type de poste | Fonctionnement / investissement, et temps de travail **par poste** |
| Par organisme + type de budget + type de poste | Le niveau le plus détaillé |

Lorsque le mode inclut le type de budget, deux cases s'ajoutent :

- **« Déclinaison par type de coût »** : détaille le budget en coût salarial, coût stage, coût
  prestataire et autres coûts (décochée, seuls les totaux de fonctionnement et d'investissement
  sont saisis) ;
- **« Saisie automatique du coût salarial »** (modes « + type de poste ») : calcule le coût
  salarial à partir des jours saisis et du coût jour des postes (voir 2.3).

Le **temps de travail** distingue le temps agent (gestionnaire) et le temps partenaire / bénévole
(valorisé), avec une catégorie de dépense (fonctionnement, investissement, bénévolat
partenariat). Une nouvelle action **reprend le paramétrage** de ventilation de la dernière action
saisie dans le plan.
:::

Le formulaire propose deux boutons :

- **[Enregistrer le brouillon]{.nouveau}** : sauvegarde votre saisie **sans tout valider** et vous
  laisse sur le formulaire (idéal pour saisir progressivement) [; l'action apparaît alors comme
  « Brouillon » dans les listes]{.nouveau} ;
- **Valider** : contrôle que tous les champs requis sont remplis, puis enregistre l'action.

> 📸 **Capture [23]{.nouveau} — Formulaire d'une action** \
> **Écran :** formulaire de création d'une action, avec le type d'action, [le code de l'action et la section « Programmation »]{.nouveau}. \
> **À mettre en évidence :** le choix du type d'action, [le « Mode de ventilation »]{.nouveau} et les boutons « Enregistrer le brouillon » / « Valider ».

> 💡 **Cas d'usage — Une action ne correspond à aucun type proposé** \
> **Situation :** l'action de mon plan ne se range dans aucun des types d'action de la liste. \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

::: nouveau
> 💡 **Cas d'usage — Mon plan d'origine n'a qu'un budget global, sans détail** \
> **Situation :** mon plan historique donne un montant total par action (voire pour tout le plan), sans répartition par année, organisme ou type de coût. \
> **Ce que propose CICADA :** le mode « Pas de ventilation », ou la case « Déclinaison par type de coût » décochée. \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

> 💡 **Cas d'usage — Mon suivi n'utilise pas un protocole standardisé, ou l'adapte** \
> **Situation :** mon suivi s'inspire d'un protocole connu (STOC, MhéO…) sans le respecter entièrement. \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

## 2.9 La fiche action

Chaque action dispose d'une **fiche** de consultation qui rassemble toutes ses informations :
indicateurs et métriques liés, description, protocole et objectifs, temporalité, acteurs,
programmation (budget, détail des coûts, temps de travail, financements), indicateurs de réponse,
emprise spatiale et réalisation.

Depuis la fiche, vous pouvez :

- **« Voir dans le plan de gestion »** : ouvrir l'enjeu à l'endroit de l'action ;
- **« Voir le suivi de l'action »** ;
- **« Exporter ou imprimer »** : au format **Impression / PDF** (en choisissant les sections à
  inclure) ou **Excel** ;
- **Modifier** l'action (plan en brouillon).

> 📸 **Capture 24 — Fiche action et fenêtre « Exporter ou imprimer »** \
> **Écran :** fiche d'une action de suivi, avec la fenêtre « Exporter ou imprimer la fiche action » ouverte. \
> **À mettre en évidence :** le choix du format et la liste « Sections à inclure ».
:::

## 2.10 Le suivi du plan

Le menu **Suivis** propose trois vues complémentaires : **Tableau de bord**, **Suivi des
actions** et **Bilan**. [Elles sont réservées aux référents du plan et aux administrateurs.]{.nouveau}

La saisie du suivi n'est possible que lorsque le plan est **validé** [(ou modifié)]{.nouveau}.

### Le tableau de bord

Une grille **[objectifs]{.nouveau} × années** affiche, par année, le **score** de chaque indicateur
(de « Très mauvais » à « Très bon », ou « Indéterminé »).

::: nouveau
- Trois vues : **État** (objectifs à long terme et niveaux d'exigence), **Pression** (objectifs
  opérationnels et résultats attendus) ou **Ensemble** (regroupé par enjeu).
- Filtres par **objectif** et par **enjeu** (choix multiple), et recherche.
- Un chevron déplie les **métriques** de chaque indicateur.
- La colonne **Global** donne l'évaluation sur toute la période ; la colonne **Actions** liste les
  actions liées.
- Un clic sur une case ouvre la **saisie** de l'année.
- **« Exporter le tableau »** produit un fichier Excel mis en forme, selon la vue et les filtres
  en cours.

**Saisir un indicateur.** Pour chaque année, saisissez le résultat de chaque métrique ; le résultat
de l'indicateur est calculé **automatiquement** (moyenne pondérée des scores des métriques). Vous
pouvez cocher **« Forcer le résultat manuellement »** pour choisir un autre niveau (y compris
« Indéterminé ») en expliquant pourquoi ; décocher la case revient au calcul automatique.

**La page globale d'un indicateur** présente son état courant, sa moyenne, sa tendance, un
graphique d'évolution et le détail par métrique. Le bouton **« Ajuster manuellement
l'évaluation »** permet d'interpréter l'évaluation globale et d'ajouter un commentaire global.
:::

> 📸 **Capture [25]{.nouveau} — Tableau de bord (état / pression)** \
> **Écran :** tableau de bord d'un plan, grille des indicateurs par année avec les scores colorés. \
> **À mettre en évidence :** la grille, la légende des scores[, la bascule État / Pression / Ensemble et le bouton « Exporter le tableau »]{.nouveau}.

::: nouveau
> 📸 **Capture 26 — Saisie d'un indicateur** \
> **Écran :** page « Remplir le suivi d'un indicateur » pour une année, avec une métrique saisie. \
> **À mettre en évidence :** le résultat automatique et la case « Forcer le résultat manuellement ».
:::

### Le suivi des actions

Une grille **actions × années** pour saisir la **réalisation** des actions, ainsi que le
**budget** et les **ressources humaines** consommés. [Quatre onglets : **Planification
mensuelle**, **Réalisation**, **Budget**, **RH**.]{.nouveau}

::: nouveau
- **Filtres** : catégorie d'action, enjeu, priorité, organisme, **année** et **réalisation**
  (réalisées / non réalisées), et recherche par nom ou code.
- **Légende de réalisation** : action prévue ; prévue et réalisée ; prévue et partiellement
  réalisée ; prévue non réalisée ; réalisée non prévue ; partiellement réalisée non prévue ;
  **en cours** (sablier) ; **non commencée**.
- La colonne **Global** donne la réalisation sur toute la période et ouvre la **page globale de
  l'action**.
- Onglets **Budget** et **RH** : pour l'**année de référence** choisie, la période écoulée et le
  total du plan, le prévisionnel et le réalisé, avec l'écart (montant **restant** en vert,
  **dépassé** en rouge).
- **Planification mensuelle** : vue **Agenda** (ce mois-ci, le mois prochain, cette année) ou vue
  **Calendrier** (une ligne par action, douze mois).
- **« Exporter le tableau »** produit un fichier Excel selon l'onglet et les filtres en cours.

**Saisir la réalisation d'une action.** Pour chaque année, renseignez :

- le **niveau de réalisation** (obligatoire) : réalisée, partiellement réalisée ou non réalisée ;
- les **opérateurs** et **financeurs** effectifs de l'année ;
- le **temps de travail réalisé** (saisi avant le budget, car il calcule le coût salarial), puis le
  **budget réalisé** ;
- un commentaire, l'**emprise réalisée** (le bouton « Copier l'emprise prévue » reprend l'emprise
  programmée) et les valeurs des **indicateurs de réponse**.

Les onglets d'années couvrent **toute la durée du plan** : saisir une année non prévue enregistre
une action **réalisée non prévue**.

**La page globale d'une action** récapitule sa réalisation, son budget et son temps de travail
année par année. Le bouton **« Ajuster manuellement la réalisation »** permet de forcer la
réalisation globale et d'ajouter un commentaire global.
:::

> 📸 **Capture [27]{.nouveau} — Suivi des actions** \
> **Écran :** vue « Suivi des actions », onglet Réalisation, grille des actions par année avec les statuts de réalisation. \
> **À mettre en évidence :** une cellule de réalisation, [la colonne Global,]{.nouveau} les onglets [Planification mensuelle /]{.nouveau} Réalisation / Budget / RH [et les filtres]{.nouveau}.

::: nouveau
> 📸 **Capture 28 — Saisie de la réalisation d'une action** \
> **Écran :** page « Remplir le suivi d'une action » pour une année. \
> **À mettre en évidence :** les onglets d'années (prévue / non prévue), le niveau de réalisation et le temps de travail réalisé.
:::

### Le bilan de la gestion

[Le **Bilan de la gestion** synthétise les résultats, selon trois **portées** : **Global**,
**Mi-parcours** (première moitié du plan) ou **Annuel** (une année choisie), et peut être filtré
par enjeu / FCR.]{.nouveau}

::: nouveau
- Onglet **Indicateurs** : répartition des scores, évaluation des indicateurs, évolution de la
  moyenne (avec minimum, maximum et écart-type) et graphique radar par enjeu.
- Onglet **Actions** : budget prévisionnel et réel (fonctionnement, investissement), jours de RH,
  taux de réalisation, niveau de réalisation par catégorie d'action, par enjeu et par année.
- **« Exporter les résultats »** : les résultats chiffrés (fichier CSV, lisible dans Excel) ou les
  graphiques (image JPG), selon les filtres en cours.
:::

> 📸 **Capture [29]{.nouveau} — Bilan de gestion** \
> **Écran :** page Bilan, onglet Actions, portée Global. \
> **À mettre en évidence :** [le choix de portée Global / Mi-parcours / Annuel, les graphiques et le bouton « Exporter les résultats »]{.nouveau}.

> 💡 **Cas d'usage — Reprendre un historique de réalisations sur plusieurs années** \
> **Situation :** mon plan existant a déjà plusieurs années de mise en œuvre ; je dois saisir rétroactivement la réalisation des actions année par année. \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

::: nouveau
> 💡 **Cas d'usage — Mes mesures passées ne rentrent pas dans la grille de la métrique** \
> **Situation :** mes mesures historiques ont été faites avec une autre méthode, ou ne permettent pas de calculer un score. \
> **Ce que propose CICADA :** forcer le résultat manuellement (y compris « Indéterminé ») en indiquant la raison. \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

> 💡 **Cas d'usage — Une action a été réalisée sans avoir été prévue** \
> **Situation :** une action du plan a été menée une année où elle n'était pas programmée. \
> **Ce que propose CICADA :** saisir la réalisation sur l'année non prévue (action « réalisée non prévue »). \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_
:::

## 2.11 Le tableau d'arborescence

Le **tableau d'arborescence** offre une vue d'ensemble cartographiée du plan : du plan vers les
enjeux, les objectifs, les indicateurs et les actions. [Un clic sur un élément]{.nouveau} permet
de **zoomer** dessus [(« Vue d'ensemble » pour revenir), un double-clic ouvre sa fiche]{.nouveau}.
Vous pouvez **replier/déplier** les branches [(ou « Tout déplier » / « Tout replier »)]{.nouveau}
et **basculer** entre la vue [« Enjeux → Actions » et la vue « Actions → Enjeux »]{.nouveau}.

> 📸 **Capture [30]{.nouveau} — Tableau d'arborescence** \
> **Écran :** vue arborescente du plan, avec plusieurs niveaux dépliés. \
> **À mettre en évidence :** le bouton de bascule [Enjeux → Actions / Actions → Enjeux]{.nouveau} et la légende des couleurs.

## 2.12 Les documents du plan

Dans la vue d'ensemble, la section **Documents** permet de **joindre** des fichiers au plan
(rapports, cartes…)[, en précisant leur type (document principal, annexe, carte, photographie,
rapport d'étude, autre)]{.nouveau}, de les **télécharger** et de les **supprimer**. [L'ajout et
la suppression ne sont possibles que sur un plan en brouillon.]{.nouveau}

> 💡 **Cas d'usage — Je veux joindre le PDF complet de mon plan d'origine** \
> **Situation :** je dispose du document complet de mon plan de gestion historique et je souhaite le conserver dans CICADA en pièce jointe. \
> [**Ce que propose CICADA :** type de document « Document principal ».]{.nouveau} \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

::: nouveau
## 2.13 Les exports du plan

La rubrique **Exports** permet de télécharger le contenu du plan. Elle est réservée aux référents
du plan et aux administrateurs.

| Groupe | Export |
|--------|--------|
| Documents du plan | Fiche plan de gestion (Word) |
| | Arborescence (présentation, Excel imprimable) |
| | Fiches action (Excel) |
| Budget et ressources humaines | Budget prévisionnel (Excel) |
| | Suivi budgétaire (Excel) |
| | RH prévisionnelles (Excel) |
| | Suivi RH (Excel) |
| Données brutes | Contenu du plan (Excel, au format du modèle d'import : réimportable dans un autre plan en brouillon) |

Les tableaux de suivi (tableau de bord, suivi des actions, bilan) et la fiche d'une action ont
aussi leur propre bouton d'export (voir 2.9 et 2.10).

> 📸 **Capture 31 — Page Exports** \
> **Écran :** page « Exports du plan de gestion » avec les trois groupes d'exports. \
> **À mettre en évidence :** les groupes « Documents du plan », « Budget et ressources humaines » et « Données brutes ».

## 2.14 Le module Mes inventaires et suivis

Le module **Mes inventaires et suivis** recense les inventaires et suivis scientifiques, qu'ils
soient inscrits ou non dans un plan de gestion. La liste peut être filtrée par **statut** (en
cours, terminé, à venir), par **site** et par **date de début**.

Le bouton **« Ajouter un inventaire/suivi »** ouvre un formulaire : intitulé, type, lien avec un
plan de gestion et un indicateur, objectifs, cibles, date de lancement, statut, fréquence,
**protocoles** (plusieurs possibles, standardisés ou non) et bancarisation de la donnée.

Un suivi saisi ici peut ensuite être rattaché à une action de suivi (type CS) d'un plan : à la
question « Inventaire ou suivi déjà saisi dans le module Mes inventaires et suivis ? », répondez
« Oui » et choisissez-le dans la liste.

> 📸 **Capture 32 — Liste des inventaires et suivis** \
> **Écran :** page « Inventaires et suivis scientifiques » avec quelques suivis. \
> **À mettre en évidence :** les filtres Statut / Site / Début et le bouton « Ajouter un inventaire/suivi ».
:::

---
---

# Partie 3 — Notice Administrateur de sites

> **À qui s'adresse cette notice ?**
> Aux **administrateurs d'organisme** : ils gèrent les utilisateurs et les sites de leur structure.
> Lisez d'abord les **Parties 1 et 2** pour les fonctions de base et la gestion des plans.
>
> **Ce que vous pouvez faire en plus :**
> - gérer les utilisateurs de votre organisme ;
> - créer et gérer les sites [(y compris par import en masse)]{.nouveau} ;
> - traiter les demandes de validation de votre périmètre ;
> - repérer les sites « orphelins ».

> ℹ️ **Voir les Parties 1 et 2** pour : les fonctions de base et la saisie/suivi des plans.

> ⚠️ **Périmètre :** en tant qu'administrateur d'organisme, vous ne voyez et ne gérez que les
> utilisateurs et les sites **de votre organisme**. [Dans les listes de plans et de sites, un
> sélecteur « Mes plans / Plans de mon organisme » (ou « Mes sites / Mon organisme ») vous permet
> d'élargir l'affichage à tout votre organisme.]{.nouveau} [Vous pouvez gérer le cycle de vie et les
> exports de tous les plans de votre organisme.]{.nouveau}

## 3.1 Accéder à l'espace d'administration

Un accès **Administration** apparaît dans l'en-tête (et dans le menu latéral). Il ouvre[, dans un
nouvel onglet,]{.nouveau} les pages réservées aux administrateurs : [validations, utilisateurs,
organismes, sites, plans de gestion, orphelins]{.nouveau}.

> 📸 **Capture [33]{.nouveau} — Espace d'administration + liste des utilisateurs** \
> **Écran :** menu latéral d'administration ouvert, sur la page « Utilisateurs ». \
> **À mettre en évidence :** le menu latéral d'administration et le tableau des utilisateurs.

## 3.2 Gérer les utilisateurs

La page **Utilisateurs** liste les comptes de votre organisme. Vous pouvez rechercher et filtrer
(par rôle, [par organisme,]{.nouveau} par statut). Pour chaque utilisateur, vous pouvez :

- l'**associer à un site** [(« Assigner un site »)]{.nouveau} ;
- le [**retirer de votre organisme**]{.nouveau} ;
- demander sa **promotion** ou sa **rétrogradation** en tant qu'administrateur d'organisme (avec
  justification[ ; la demande est soumise aux super administrateurs]{.nouveau}).

[L'activation et la désactivation des comptes sont réservées au super administrateur.]{.nouveau}

## 3.3 Gérer les sites

La page **Sites** liste les sites de votre organisme. Vous pouvez :

- **créer** ou **modifier** un site : nom, type, surface, **code INPN**, [identifiant local, site
  marin,]{.nouveau} et tracé sur la carte [(ou import d'un fichier GeoJSON / Shapefile)]{.nouveau} ;
- **lier des organismes** au site (dont l'organisme principal) ;
- **associer des utilisateurs** (référents ou membres) [(« Gérer les utilisateurs »)]{.nouveau} ;
- **supprimer** un site (un avertissement signale les plans et utilisateurs rattachés).

À la création, CICADA détecte les **doublons** : si le code INPN existe déjà, la création est
bloquée ; si un nom ressemble à un site existant, une suggestion non bloquante s'affiche [(avec
les choix « Demander l'accès », « Lier mon organisme et demander l'accès », « Lier mon organisme
uniquement » ou « Ignorer les suggestions »)]{.nouveau}.

> 📸 **Capture [34]{.nouveau} — Formulaire de site + détection de doublon INPN** \
> **Écran :** formulaire de création d'un site avec la carte, et l'avertissement de doublon INPN. \
> **À mettre en évidence :** le champ code INPN et le panneau « Sites existants ».

> 📸 **Capture [35]{.nouveau} — Associer un utilisateur à un site** \
> **Écran :** fenêtre d'association utilisateur ↔ site, avec le choix référent / membre. \
> **À mettre en évidence :** la case « référent » et la liste des utilisateurs.

> 💡 **Cas d'usage — Le site existe déjà dans CICADA (rattachement ou doublon ?)** \
> **Situation :** je veux ajouter un site, mais CICADA m'indique qu'un site identique (ou très proche) existe déjà. Dois-je demander un rattachement ou créer malgré tout ? \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

::: nouveau
## 3.4 Importer des sites en masse

Depuis le module **Sites**, le bouton **« Import en masse de sites »** ouvre un assistant en
**quatre étapes** :

1. **Fichier** : déposer un fichier de sites (GeoJSON ou CSV, 10 Mo au maximum ; seul le GeoJSON
   contient les contours) ;
2. **Correspondance** : associer les colonnes du fichier aux champs de CICADA ;
3. **Vérification** : prévisualiser les sites, repérer les erreurs et les doublons INPN ;
4. **Résultats** : lancer l'import et consulter le bilan (créés / ignorés).

Deux colonnes facultatives évitent de rattacher tout un import à une seule structure :
**Organisme gestionnaire** (nom ou identifiant de l'organisme) et **Référent** (e-mail ou
identifiant de l'utilisateur). Chaque site est alors rattaché à sa propre structure et à ses
propres référents. Plusieurs valeurs se séparent par un point-virgule (« CEN A ; CEN B ») ; le
premier organisme cité devient le gestionnaire principal. Une valeur introuvable n'empêche pas
l'import : elle est signalée en avertissement à l'étape de vérification, et la ligne est rattachée
à votre organisme (et à vous comme référent). Un administrateur d'organisme ne peut rattacher que
les utilisateurs de son propre organisme.

> 📸 **Capture 36 — Import en masse (étape Vérification)** \
> **Écran :** étape de vérification de l'import, avec le tableau de prévisualisation et les doublons signalés. \
> **À mettre en évidence :** les colonnes Organisme / Référent, les lignes en erreur / doublon et le bouton « Importer les sites sélectionnés ».
:::

## 3.5 Gérer son organisme

La page **Organismes** vous permet de consulter et de modifier les informations de votre organisme,
et d'y **rattacher des utilisateurs et des sites** [(« Ajouter un utilisateur », « Ajouter un
site », « Créer un site »)]{.nouveau}.

## 3.6 Traiter les validations

La page **Validations** rassemble les demandes à traiter sur votre périmètre (inscriptions, accès
à un site ou un plan, créations de site, rattachements[, créations d'organisme]{.nouveau}…). Vous
pouvez **approuver** ou **rejeter** chaque demande, soit rapidement depuis la liste, soit via une
**fenêtre de détail** qui affiche le contexte complet (et, le cas échéant, le choix entre rôle
« référent » et « utilisateur »). [Un commentaire est obligatoire pour un rejet.]{.nouveau}

::: nouveau
Pour une inscription, la fenêtre indique si l'**organisme a déjà un administrateur** :
« Nouvel organisme », « Cet organisme n'a aucun administrateur » (pensez alors à promouvoir le
compte après l'avoir accepté) ou « Cet organisme a déjà N administrateur(s) ». Des avertissements
rappellent aussi l'ordre de traitement (par exemple, valider le lien organisme–site avant l'accès
au site).
:::

> 📸 **Capture [37]{.nouveau} — Liste des validations à traiter** \
> **Écran :** tableau des demandes de validation, avec leurs types, statuts et boutons d'action. \
> **État à reproduire :** quelques demandes « en attente ». \
> **À mettre en évidence :** les boutons « Approuver » / « Rejeter » et la colonne « Statut ».

> 📸 **Capture [38]{.nouveau} — Fenêtre de détail d'une validation** \
> **Écran :** fenêtre « Traiter la demande » pour une inscription, avec le contexte et la zone de commentaire. \
> **À mettre en évidence :** le contexte de la demande, [la mention sur les administrateurs de l'organisme]{.nouveau} et le choix référent / utilisateur.

## 3.7 Repérer les sites orphelins

La page **Orphelins** liste les **sites sans aucun utilisateur** de votre organisme. Vous pouvez y
**rattacher des utilisateurs** [(bouton « Gérer »)]{.nouveau} pour éviter qu'un site reste sans
gestionnaire. [Un compteur dans le menu d'administration signale leur nombre.]{.nouveau}

> 📸 **Capture [39]{.nouveau} — Page Orphelins** \
> **Écran :** page « Sites et plans orphelins » avec la liste des sites sans utilisateur. \
> **À mettre en évidence :** la liste des sites orphelins et le bouton « Gérer ».

> 💡 **Cas d'usage — Un utilisateur intervient pour plusieurs organismes** \
> **Situation :** une même personne travaille pour plusieurs structures et doit accéder à des sites relevant d'organismes différents. \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_

---
---

# Partie 4 — Notice Administrateur de l'application

> **À qui s'adresse cette notice ?**
> Au **super administrateur**, qui pilote l'ensemble de CICADA, sans limite de périmètre.
> Cette notice **inclut tout ce qui précède** (Parties 1 à 3), appliqué à la totalité des
> organismes, sites et plans.
>
> **Ce que vous pouvez faire en plus :**
> - superviser l'activité globale ;
> - gérer tous les utilisateurs (dont l'impersonation) et les [rédacteurs généraux]{.nouveau} ;
> - gérer les modules, les journaux d'erreurs[ et du serveur]{.nouveau}, les demandes RGPD, les
>   paramètres et les mises à jour.

> ℹ️ **Voir les Parties 1 à 3** pour les fonctions communes et la gestion par organisme[, dont
> l'import en masse de sites]{.nouveau}.

[Le **numéro de version** de CICADA est affiché en bas du menu d'administration.]{.nouveau}

## 4.1 Le tableau de bord global

Le **tableau de bord** présente les statistiques de l'ensemble de l'application : nombre de plans
(et plans actifs), d'utilisateurs, de sites et d'organismes.

> 📸 **Capture [40]{.nouveau} — Tableau de bord global** \
> **Écran :** tableau de bord d'administration avec les cartes de statistiques. \
> **À mettre en évidence :** les compteurs (plans, utilisateurs, sites, organismes).

## 4.2 Gérer tous les utilisateurs et l'impersonation

Vous gérez les utilisateurs **de tous les organismes** [: assigner un organisme, activer ou
désactiver un compte (un motif est demandé à la désactivation)]{.nouveau}.

[**Promouvoir ou rétrograder un administrateur d'organisme** : en tant que super administrateur,
le changement prend effet **immédiatement, sans demande de validation** (la justification est
facultative).]{.nouveau}

Vous disposez en plus du **mode visualisation** (« impersonation ») [(icône œil « Voir en tant que
cet utilisateur »)]{.nouveau} : vous pouvez naviguer dans l'application **en tant qu'un autre
utilisateur** pour voir exactement ce qu'il voit[, en lecture seule]{.nouveau}. Un **bandeau**
rappelle en permanence que vous êtes en mode visualisation et propose de **revenir à votre
compte**.

> 📸 **Capture [41]{.nouveau} — Bandeau de mode visualisation (impersonation)** \
> **Écran :** une page de l'application avec le bandeau « Mode visualisation » en haut. \
> **À mettre en évidence :** le bandeau, [le badge « Mode lecture seule »]{.nouveau} et le bouton « Revenir à mon compte ».

## 4.3 Gérer les [rédacteurs généraux]{.nouveau}

La page **[Rédacteurs généraux]{.nouveau}** permet d'**attribuer** ou de **retirer** ce rôle, qui
donne un accès étendu (en lecture/écriture) à l'ensemble des plans, sites et organismes. [Le
rédacteur général ne peut toutefois pas supprimer un site, ni accéder aux pages réservées au super
administrateur (tableau de bord, paramètres, journaux, RGPD, modules, mise à jour).]{.nouveau}

## 4.4 Gérer les modules

La page **[Accès modules]{.nouveau}** permet de **donner ou retirer l'accès** aux différents
modules de l'application et de traiter les **demandes d'accès** en attente.

## 4.5 Consulter les journaux d'erreurs [et du serveur]{.nouveau}

La page **[Logs erreurs]{.nouveau}** liste les incidents techniques (avec leur niveau de gravité).
Vous pouvez filtrer, consulter le détail et **acquitter** une erreur (ou toutes).

[La page **Logs serveur** permet de consulter les fichiers de journaux de l'application (général,
erreurs, audit des actions), filtrés par niveau, et de les **télécharger**.]{.nouveau}

> 📸 **Capture [42]{.nouveau} — Journaux d'erreurs** \
> **Écran :** tableau des journaux d'erreurs avec les niveaux de gravité et le bouton d'acquittement. \
> **À mettre en évidence :** la colonne « Niveau » et le bouton « Tout acquitter ».

## 4.6 Traiter les demandes RGPD

La page **RGPD** liste les demandes de suppression de compte. Pour chacune, vous pouvez
**désactiver**, **anonymiser** ou **rejeter** la demande, en tenant compte du délai légal.

## 4.7 Paramètres et mise à jour

- **Paramètres** :
  - personnaliser l'**image d'accueil** de l'application et sa position (haut, centre, bas) ;
  - [choisir la **couleur du bandeau** (couleurs proposées ou personnalisée, avec aperçu)
    et ajouter le **logo de la structure**, affiché en haut à gauche ;]{.nouveau}
  - [choisir la **couleur des exports** Excel et Word (les couleurs des scores ne changent pas) ;]{.nouveau}
  - [**afficher le champ « ID Doc'Gestion FCEN »** dans les plans (à n'activer que sur l'instance
    de la FCEN) ;]{.nouveau}
  - [**ouvrir l'API publique des métadonnées des plans** : permet à une application tierce de
    gestion documentaire de lire les métadonnées des plans (jamais leur contenu, leur budget ni
    les brouillons) ;]{.nouveau}
  - [**partager les plans avec l'exploration nationale** : voir ci-dessous.]{.nouveau}
- **Mise à jour** : consulter la version installée et la dernière version disponible, et
  **déclencher** une mise à jour.

::: nouveau
**Le partage avec l'exploration nationale** est un **engagement de la structure**. Lorsque la case
est cochée :

- les plans **validés** de l'instance sont publiés chaque nuit vers l'exploration nationale :
  enjeux, facteurs, pressions, objectifs, indicateurs, actions avec leur période, suivis et
  protocoles ;
- **ne sont jamais partagés** : budget et financements, ressources humaines, mesures et
  réalisations, auteurs ;
- en contrepartie, les utilisateurs de l'instance explorent les plans de **toutes les structures
  participantes**.

Lorsque la case est décochée, l'exploration porte uniquement sur les plans de l'instance.
Décocher la case arrête les publications à venir mais **n'efface pas** ce qui a déjà été publié :
le retrait doit être demandé à l'administrateur système.
:::

> 📸 **Capture [43]{.nouveau} — Paramètres de l'application** \
> **Écran :** page Paramètres avec l'aperçu de l'image d'accueil[, la couleur du bandeau et la case de partage avec l'exploration nationale]{.nouveau}. \
> **À mettre en évidence :** l'aperçu de l'image, [l'aperçu du bandeau et la section « Partage avec l'exploration nationale »]{.nouveau}.

::: nouveau
> 💡 **Cas d'usage — Faut-il partager nos plans avec l'exploration nationale ?** \
> **Situation :** ma structure hésite à activer le partage : qui décide, et à quel moment ? \
> **Réponse (à compléter) :** \
> _…………………………………………………………………………………………………_
:::

---
---

# Modules à venir

CICADA continue d'évoluer. Le module suivant est **en cours de développement** et sera documenté
dans une prochaine version de cette notice :

- **Zonages réglementaires** — saisie et visualisation des zonages. [Il apparaît déjà dans le
  menu, grisé avec la mention « Prochainement », pour les utilisateurs qui y ont accès.]{.nouveau}
  > 💡 **Espace réservé — à compléter à la mise à disposition du module.**
  > _…………………………………………………………………………………………………_

[Le module **Exploration des données des plans de gestion**, annoncé dans la version précédente,
est désormais disponible : voir Partie 1, section 1.10.]{.nouveau}

> ℹ️ Cette notice sera enrichie au fur et à mesure de l'ouverture de ces modules. Les encadrés
> **« Cas d'usage »** laissés vides dans les parties précédentes sont également destinés à être
> complétés par votre réseau, à partir des situations rencontrées pendant la phase de saisie des
> plans existants.
