# API de CICADA

CICADA expose une **API REST** (Django REST Framework) : c'est elle que consomme l'application web, et elle est ouverte aux intégrations tierces et aux développements. Chaque instance CICADA expose sa propre API à l'adresse `https://<instance>/api/` ; il n'existe pas d'API centrale.

<div class="tiles">

<a href="prise-en-main/" class="tile--green">
<strong>Prise en main</strong>
Premier appel en cinq minutes : jeton, en-têtes, pagination, filtres, format des erreurs.
</a>

<a href="authentification/" class="tile--yellow">
<strong>Authentification et permissions</strong>
Jetons JWT, mode de connexion de l'instance, rôles et règles d'accès transverses.
</a>

<a href="reference/" class="tile--salmon">
<strong>Référence complète</strong>
Les 300 endpoints dans une seule interface Swagger, avec filtre.
</a>

</div>

## Les domaines de l'API

Chaque page décrit un domaine fonctionnel, ses règles, des exemples d'appels, puis embarque la **référence Swagger** des endpoints concernés (générée depuis le code).

| Domaine | Préfixes | Ce qu'on y fait |
|---------|----------|-----------------|
| [Authentification](auth.md) | `/api/auth/` | Connexion, inscription, mot de passe, impersonation |
| [Utilisateurs](users.md) | `/api/users/users/`, `/api/users/permissions/` | Comptes, rôles, droits, RGPD |
| [Organismes et sites](organismes-sites.md) | `/api/users/organismes/`, `/api/users/sites/`, `/api/geo/` | Structures gestionnaires, sites, géométries, import en masse |
| [Plans de gestion](plans.md) | `/api/plans/plans/`, `/api/plans/fichiers/`, `/api/plans/responsabilites/` | Plans, cycle de vie, versions, imports Excel, exports, documents |
| [Arborescence](arborescence.md) | `/api/plans/enjeux/` … `/api/plans/mesures/` | Enjeux, facteurs, pressions, objectifs, indicateurs, métriques, mesures |
| [Actions et suivi](actions-suivi.md) | `/api/plans/operations/`, `/api/plans/realisations/`, `/api/plans/postes/`, `/api/inventaires/` | Actions, programmation, réalisation, bilan, postes, inventaires et suivis |
| [Référentiels](referentiels.md) | `/api/taxref/`, `/api/habref/`, `/api/inpg/`, `/api/campanule/`, `/api/nomenclatures/` | TaxRef, HabRef, INPG, protocoles standardisés, nomenclatures |
| [Notifications, validations et activité](notifications.md) | `/api/notifications/`, `/api/validations/`, `/api/activity/`, `/api/modules/` | Demandes de validation, notifications, historique, accès aux modules |
| [Exploration et fédération](exploration.md) | `/api/exploration/`, `/api/federation/` | Recherche dans les plans validés, hub national, raccordement |
| [Administration de l'instance](administration.md) | `/api/settings/`, `/api/admin/`, `/api/system/` | Paramètres, journaux, orphelins, version et mise à jour |
| [API publique des métadonnées](api-publique-plans.md) | `/api/public/` | Lecture ouverte des métadonnées des plans validés |

## Principes généraux

- **Format** : JSON en entrée comme en sortie (`Content-Type: application/json`), sauf téléversements (`multipart/form-data`) et exports (fichiers Excel, Word, GeoJSON). Les géométries sont échangées en **GeoJSON**, en WGS 84 (EPSG:4326).
- **Authentification** : jeton JWT sur tous les endpoints, sauf `/api/auth/` (connexion, inscription), `/api/health/`, la configuration publique de l'instance et, lorsqu'elle a été ouverte, l'[API publique des métadonnées](api-publique-plans.md).
- **Pagination** : les listes sont paginées (voir [Prise en main](prise-en-main.md#pagination)).
- **Filtrage, recherche et tri** : `?champ=valeur`, `?search=` et `?ordering=` sur la plupart des listes ; chaque page Swagger détaille les paramètres disponibles.
- **Droits** : l'API applique exactement les règles de l'application (voir [Authentification et permissions](authentification.md)). Un plan qui n'est pas en brouillon est en **lecture seule** pour tout le monde ; seuls les actions de cycle de vie et les exports restent possibles, pour ses référents et les gestionnaires.
- **Traçabilité** : chaque requête reçoit un identifiant `X-Correlation-ID`, renvoyé dans les réponses d'erreur et propagé dans les journaux du serveur.
- **Essayer un appel** : sur les pages Swagger de cette documentation, « Try it out » n'est proposé que pour les lectures (`GET`) et interroge l'instance qui la sert. Les écritures s'essaient sur `/api/docs/` de l'instance, avec un jeton.
- **Schéma OpenAPI** : sur une instance, le schéma vivant est servi à `/api/schema/` et Swagger UI à `/api/docs/` (utilisateur authentifié). Cette documentation en embarque une copie, générée par `drf-spectacular` à chaque version.
