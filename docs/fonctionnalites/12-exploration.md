# 12. Exploration des données

L'exploration permet à tout utilisateur connecté de **chercher dans le contenu des plans validés** : enjeux, pressions, objectifs, indicateurs, actions. Elle sert à s'inspirer de ce que font d'autres gestionnaires, sur son instance ou, avec le hub, sur toutes les instances.

> Usage pas à pas : notice utilisateur. Détail de l'index : [RECHERCHE.md](../RECHERCHE.md). Fédération : [21. Exploration fédérée](21-federation.md).

## Deux modes de résultat

| Mode | Route | Ce qu'il renvoie |
|------|-------|------------------|
| **Plans** | `/exploration/plans` | Une tuile par plan, avec ses facettes (type d'aire, région, statut…) |
| **Contenus** | `/exploration/contenus` | Une ligne par objet trouvé (enjeu, action…), avec son plan |

Un clic ouvre la **fiche** du plan (`/exploration/plans/:slug`), puis ses écrans réels en lecture seule, **sans données sensibles** : ni budget, ni RH, ni mesures, ni personnes (#683, `apps/plans/exploration.py`).

## L'index de recherche

- Table dénormalisée `ccd_search.t_recherche_contenu` : une ligne par objet d'un plan **validé, modifié ou archivé**, avec ses facettes et deux `tsvector` générés (titres seuls, ou texte élargi). PostgreSQL seulement, pas d'Elasticsearch.
- Construction : `apps/search/indexing.py` (`construire_documents()`), mise à jour par signaux, reconstruction par `manage.py rebuild_search_index`.
- Les codes de référentiel (`codes_referentiel` : types d'action, PressRef, TaxRef, HabRef) permettent de filtrer par type ou catégorie, **équivalences entre versions comprises** (#780).

## Filtres

Texte (titres seuls ou élargi), type de contenu, type d'aire protégée, zone géographique (région, département), types d'action et catégories, pressions, taxons, habitats, structure d'origine (`?instances=`). Ils sont écrits dans `apps/search/filters.py`, **en deux exemplaires** (CICADA et hub), gardés identiques par les tests de parité du banc de fédération.

## Provenance

Chaque résultat dit de quelle structure il vient (`instance_id`, `instance_libelle`), en local comme en fédéré (#692) : pastille `app-provenance-tag` sur chaque tuile et chaque ligne. Une URL d'exploration se partage d'une instance à l'autre.

## API

| Endpoint | Rôle |
|----------|------|
| `GET /api/exploration/plans/`, `…/contenus/` | Recherche |
| `GET /api/exploration/plans/{reference}/` | Fiche d'un plan (`instance:slug` ou slug) |
| `GET /api/exploration/instances/` | Structures présentes dans l'index |

En mode `hub`, l'instance relaie ces appels vers le hub ; si le hub ne répond pas, **502** explicite, jamais de repli silencieux sur l'index local.

## Fichiers

| Fichier | Rôle |
|---------|------|
| `backend/apps/search/` | Index, filtres, vues, publication vers le hub |
| `frontend/src/app/features/exploration/` | Pages Plans, Contenus, Fiche, filtres, bannière de portée |
| `frontend/src/app/core/models/exploration.model.ts` | Modèles, `referencePlan()` |

---

← [Configuration](11-configuration.md) | [Index](../FONCTIONNALITES.md) | [Données de test](13-seeders.md) →
