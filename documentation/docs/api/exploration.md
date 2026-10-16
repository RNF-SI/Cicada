# Exploration et fédération

L'**exploration des données** cherche dans le contenu des plans de gestion **validés** (jamais les brouillons). Selon le réglage de l'instance, elle porte sur l'index local ou, via le **hub** national, sur les plans de toutes les structures qui partagent. Le navigateur n'appelle jamais le hub : l'instance relaie, et la forme des réponses est la même dans les deux cas.

## Recherche

| Endpoint | Rôle |
|----------|------|
| `GET /api/exploration/contenus/` | Mode « un contenu d'un plan » : enjeux, facteurs, pressions, objectifs, indicateurs, actions, suivis portant le mot cherché |
| `GET /api/exploration/plans/` | Mode « un plan de gestion » : plans d'un site, d'un département, d'une région, ou par nom |
| `GET /api/exploration/plans/{slug}/` | Fiche publique d'un plan (instantané publié, élagué des données sensibles) ; `slug` vaut `instance:slug` pour un plan distant |
| `GET /api/exploration/distant/{reference}/{chemin}` | Écrans réels d'un plan distant (arborescence, fiche action) relayés depuis l'instance d'origine |
| `GET /api/exploration/instances/` | Structures présentes dans l'index : libellé, URL, volumes, dernière publication |

Paramètres communs : `q` (mot-clé, fautes de frappe tolérées), `type` (type d'élément), portée de la recherche (`descriptions`, `parents`, `enfants`), zone géographique (codes INSEE de régions et départements), `instances` (structures d'origine), `tri` (pertinence, alphabétique, récents), pagination. Chaque résultat indique pourquoi il répond (titre, description, parent, enfant, espèce ou habitat rattaché, zone), son fil d'arborescence, son plan, ses sites, sa période, et sa **provenance** (`instance_id`, `instance_libelle`).

## Portée et réciprocité

- La portée (locale ou nationale) est annoncée par `GET /api/exploration/instances/` : une seule structure en local, plusieurs en national.
- En mode relayé, si le hub est injoignable l'API répond **`502`** sans repli sur l'index local : une recherche « nationale » qui ne renverrait que les plans locaux ferait conclure, à tort, que les autres structures n'ont rien.
- **Qui ne partage pas ne lit pas** : la lecture du hub est refusée à une instance qui n'a rien publié. Le partage se règle dans les [paramètres de l'instance](administration.md) (`federation_partage`).

## Fédération (côté instance)

| Endpoint | Rôle |
|----------|------|
| `GET /api/exploration/federation/documents/` | L'index local tel qu'il serait publié vers le hub (diagnostic) |
| `GET /api/federation/raccordement/` | État du raccordement de l'instance au hub (jetons, dernière publication, retrait en attente) |
| `POST /api/federation/raccordement/verifier/` | Teste la liaison avec le hub |
| `POST /api/federation/raccordement/adhesion/`, `…/confirmation/`, `…/contact/` | Demande d'adhésion (qui vaut consentement au partage), saisie du code reçu, contact du gestionnaire du hub |

La publication elle-même (lot, pages, bascule) est faite par l'instance vers l'API du hub chaque nuit, ou à la demande par la commande `push_federation` ; elle n'est pas exposée ici. Ce qui sort : enjeux, facteurs, pressions, objectifs, indicateurs, actions avec période, suivis, protocoles. Ce qui ne sort jamais : budget, financements, ressources humaines, mesures, réalisations, auteurs, dates.

## Référence interactive

<swagger-ui src="openapi/exploration.json"/>
