---
title: Accueil
hide:
  - navigation
---

# Documentation CICADA

## Contexte et consignes de lecture

CICADA est un outil numérique **open source** destiné à accompagner, entre autres, les gestionnaires d'aires protégées dans la **saisie et le suivi de leurs plans de gestion** selon la méthodologie **CT88**.

<figure markdown="span" class="figure--medium">
![Page d'accueil de CICADA - instance de RNF](assets/figures/fig01.png){ loading=lazy }
<figcaption>Figure 1 : Page d'accueil de CICADA - instance de RNF</figcaption>
</figure>

Développé par **Réserves Naturelles de France (RNF)** et la **Fédération des Conservatoires d'espaces naturels (FCEN)**, en partenariat avec la Ligue pour la protection des oiseaux (LPO), PatriNat et l'Office français de la biodiversité (OFB) dans le cadre du programme européen **LIFE Biodiv'France**, CICADA vise à structurer le travail des gestionnaires tout en facilitant la remontée et la valorisation des données à l'échelle des réseaux.

À ce jour, l'outil permet la saisie, le suivi et l'exploration des plans de gestion. Le module « Zonages réglementaires » sera développé en 2027. D'autres modules pourront aussi voir le jour ultérieurement, au gré des besoins et moyens disponibles.

Cette documentation rassemble trois ensembles. La **barre de recherche** en haut de page permet de retrouver directement une fonctionnalité, quel que soit l'ensemble où elle est décrite.

<div class="tiles">

<a href="utilisateur/" class="tile--green">
<strong>Guide utilisateur</strong>
La notice d'utilisation de CICADA : connexion, sites, plans de gestion, saisie, suivi, exploration des données et administration. Quatre notices selon votre profil (ci-dessous).
</a>

<a href="administration/" class="tile--yellow">
<strong>Administration technique</strong>
Installer, mettre à jour et exploiter une instance CICADA : paquet Debian, Docker, serveur Apache, hub d'exploration fédérée.
</a>

<a href="api/" class="tile--salmon">
<strong>API</strong>
Authentification, permissions, API publique des métadonnées des plans et référence complète des endpoints REST.
</a>

</div>

## Les différents rôles et profils

Le guide utilisateur rassemble quatre notices. Chacune s'adresse à un profil d'utilisateur différent. Les profils sont cumulatifs : un administrateur peut faire tout ce que fait un utilisateur simple, en plus des fonctions propres à son rôle.

| Profil | À qui s'adresse la notice | Où lire |
|--------|---------------------------|---------|
| **Utilisateur** | Toute personne disposant d'un compte CICADA | [Notice Utilisateur](utilisateur/notice/index.md) |
| **Référent de plan de gestion** | Personne(s) chargée(s) de saisir et suivre un plan (référent(s) du plan) | [Notice Référent d'un plan de gestion](referent/index.md) |
| **Administrateur d'organisme** | Responsable d'un organisme gestionnaire (CEN, RNF, Parc…) | [Notice Administrateur d'organisme](admin-organisme/index.md) |
| **Administrateur d'une instance** | Super administrateur : pilote l'ensemble de l'outil sur son instance déployée | [Notice Administrateur d'une instance](admin-instance/index.md) et [Administration technique](administration/index.md) |

!!! tip "Il existe deux profils intermédiaires :"

    - **Le rédacteur général :** il peut consulter et modifier tous les plans de gestion et tous les sites de son instance. Il utilise donc les notices [Utilisateur](utilisateur/notice/index.md), [Référent](referent/index.md) et [Administrateur d'organisme](admin-organisme/index.md). Ce rôle n'est attribuable que par le super administrateur.
    - **Le rédacteur externe :** il peut saisir et modifier un plan de gestion sur lequel il a des droits (mais n'a pas accès aux suivis). Ce profil permet à des personnes externes à l'organisme gestionnaire, de rédiger un plan (ex : prestataire). Ce rôle est attribuable par l'administrateur de l'instance ou par un référent du plan concerné.

**Les fonctions de base** (se connecter, gérer son profil, recevoir des notifications, consulter sites et plans, demander un accès) **ne sont décrites qu'une seule fois, dans la [Notice Utilisateur](utilisateur/notice/index.md)**. Les notices suivantes y renvoient et ne détaillent que ce qui est propre à chaque rôle d'administration.

Les développeurs et les intégrateurs (application documentaire tierce, connexion GeoNature, scripts) trouveront leur compte dans la partie [API](api/index.md) ; l'installation et l'exploitation d'une instance sont décrites dans l'[Administration technique](administration/index.md).

## Je veux…

Un index par besoin, qui renvoie vers la section concernée.

<dl class="jeveux" markdown>

<dt>Me connecter ou créer un compte</dt>
<dd markdown>[Se connecter](utilisateur/notice/se-connecter.md) — connexion, création de compte, déconnexion.</dd>

<dt>Suivre mes demandes d'accès et mes notifications</dt>
<dd markdown>[L'en-tête : notification, menu et profil](utilisateur/notice/en-tete.md) — cloche de notifications, page Activité, page « Mes demandes ».</dd>

<dt>Accéder à un site ou en créer un</dt>
<dd markdown>[Rejoindre ou créer un nouveau site](utilisateur/notice/rejoindre-creer-site.md) — recherche d'un site existant, demande d'accès, création avec contour cartographique.</dd>

<dt>Consulter un plan de gestion ou y demander l'accès</dt>
<dd markdown>[Consulter les plans de gestion](utilisateur/notice/consulter-plans.md) et [Comprendre la structure d'un plan de gestion](utilisateur/notice/structure-plan.md).</dd>

<dt>Rechercher dans les plans de gestion de toutes les structures</dt>
<dd markdown>[Explorer les données des plans de gestion](utilisateur/notice/exploration.md) — modes de recherche, portée, résultats.</dd>

<dt>Créer un plan de gestion</dt>
<dd markdown>[Créer un nouveau plan de gestion](referent/creer-plan.md) — informations générales, sites, fil entre les rangs.</dd>

<dt>Reprendre un plan existant depuis Excel</dt>
<dd markdown>[Le paramétrage du plan › Importer un plan depuis un fichier Excel](referent/parametrage.md#432-importer-un-plan-depuis-un-fichier-excel).</dd>

<dt>Saisir les enjeux, objectifs, indicateurs et actions</dt>
<dd markdown>[Les enjeux et leur contenu](referent/enjeux.md), [Les indicateurs et les métriques](referent/indicateurs-metriques.md), [Les actions de gestion](referent/actions.md).</dd>

<dt>Valider, prolonger, réviser ou terminer un plan</dt>
<dd markdown>[Le cycle de vie d'un plan de gestion](referent/cycle-de-vie.md).</dd>

<dt>Renseigner le suivi des indicateurs et des actions</dt>
<dd markdown>[Le suivi du plan de gestion](referent/suivi.md) — tableau de bord, suivi des actions, bilan de la gestion.</dd>

<dt>Exporter le plan en Word ou Excel</dt>
<dd markdown>[Les exports du plan](referent/exports.md).</dd>

<dt>Gérer les utilisateurs et les sites de mon organisme</dt>
<dd markdown>[Notice Administrateur d'organisme](admin-organisme/index.md) — utilisateurs, sites, import en masse, validations, orphelins.</dd>

<dt>Paramétrer mon instance, partager avec l'exploration nationale ou la mettre à jour</dt>
<dd markdown>[Paramètres de l'instance et mise à jour](admin-instance/parametres.md).</dd>

<dt>Installer, déployer ou exploiter une instance CICADA</dt>
<dd markdown>[Administration technique](administration/index.md) — installation, infrastructure, hub d'exploration fédérée, releases.</dd>

<dt>Interroger l'API ou brancher une application tierce</dt>
<dd markdown>[API](api/index.md) — [authentification et permissions](api/authentification.md), [API publique des métadonnées des plans](api/api-publique-plans.md), [référence des endpoints](api/reference.md).</dd>

</dl>
