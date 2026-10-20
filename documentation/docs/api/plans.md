# Plans de gestion

Un plan de gestion (`PlanGestion`, clé `id_pg`) couvre un ou plusieurs sites, porte des référents et des membres, un statut et une place dans une **chaîne de versions** (rang et version). Son contenu (enjeux, objectifs, indicateurs, actions) est décrit dans [Arborescence](arborescence.md) et [Actions et suivi](actions-suivi.md).

## Endpoints principaux

| Endpoint | Rôle |
|----------|------|
| `GET/POST /api/plans/plans/` | Liste (25 filtres : statut, site, organisme, années, rang…) et création |
| `GET/PUT/PATCH/DELETE /api/plans/plans/{id_pg}/` | Détail (avec `version_chain`, `peut_etre_etendu`…), modification, suppression |
| `GET /api/plans/plans/by-slug/{slug}/` | Détail par slug (adresse utilisée par l'application) |
| `GET /api/plans/plans/for-sites/?site_ids=1,2` | Plans existants sur des sites, tous statuts, groupés par site et par rang |
| `GET /api/plans/plans/recherche-acces/?q=` | Recherche d'un plan à rédiger (rédacteur externe uniquement, métadonnées seules) |
| `GET /api/plans/plans/stats/`, `…/geojson_list/`, `…/{id_pg}/geojson/`, `…/export_geojson/` | Statistiques et géométries |
| `POST /api/plans/plans/{id_pg}/assign_site/`, `…/remove_site/`, `…/replace_site/`, `POST …/bulk_assign_sites/` | Sites du plan |
| `POST /api/plans/plans/{id_pg}/assign_referent/`, `…/remove_referent/`, `…/assign_member/`, `…/remove_member/` | Référents et membres |
| `POST /api/plans/plans/{id_pg}/assign-redacteur-externe/`, `GET …/redacteurs-externes/` | Rattacher un rédacteur externe ; liste des rédacteurs externes de l'instance, tous organismes confondus (référents du plan et gestionnaires) |
| `GET /api/plans/plans/{id_pg}/mindmap/`, `…/mindmap-inverse/` | Arbre complet du plan (tableau d'arborescence), dans les deux sens |
| `GET /api/plans/plans/{id_pg}/operation-codes/`, `…/operation-code-preview/` | Codes d'affichage des actions (CS1, IP2…) |
| `GET/POST /api/plans/fichiers/`, `GET …/{id}/download/` | Documents joints au plan (type, téléchargement, suppression) |
| `GET/POST /api/plans/responsabilites/` | Responsabilités d'un site (indépendantes du cycle de vie) |

## Cycle de vie

Les statuts : `draft` (seul statut modifiable), `avis_csrpn`, `comite_consultatif`, `arrete_pref` (workflow CSRPN), `valide`, `modifie`, `archive`. Trois attributs orthogonaux s'ajoutent : `annees_extension`, `en_revision`, `is_mi_parcours`.

| Endpoint | Rôle |
|----------|------|
| `POST …/{id_pg}/change-status/` | `{ "new_status": "valide" \| "draft" \| "archive" \| …, "is_mi_parcours"?: bool }`. `draft → valide` est routé automatiquement vers `modifie` quand le parent est validé |
| `POST …/{id_pg}/csrpn-step/`, `…/admin-validation/` | Étapes CSRPN (avis, comité, arrêté) et validations administratives indépendantes |
| `POST …/{id_pg}/duplicate/` | Nouvelle version en brouillon, copie sélective du contenu |
| `POST …/{id_pg}/create-evaluation/` | Brouillon d'évaluation mi-parcours (plan source validé) |
| `POST …/{id_pg}/create-next-rang/` | Brouillon du rang suivant, version 1 |
| `POST …/{id_pg}/extend-duration/` `{ "years": 1 \| 2 }`, `…/remove-extension/` | Prolongation : crée un brouillon de version étendue (cumul maximal de 2 ans) |
| `POST …/{id_pg}/start-revision/`, `…/end-revision/` | Marquer en cours de révision, éventuellement lié à un brouillon du rang suivant |
| `POST …/{id_pg}/delete-version/` | Suppression définitive d'une version, renumérotation des suivantes |

Règles : **un seul brouillon enfant par parent** ; un brouillon ne se crée que sur un plan `valide`, `modifie` ou `archive` ; le retour en brouillon n'est possible que sur la feuille de la chaîne ; valider un brouillon valide en cascade ses parents encore en brouillon. Ces actions sont réservées aux référents du plan, à l'administrateur d'organisme, au rédacteur général et au super administrateur ; les autres écritures exigent le statut `draft`.

## Imports Excel

| Endpoint | Rôle |
|----------|------|
| `GET …/example-arborescence-xlsx/`, `…/example-actions-xlsx/`, `GET …/import-arborescence-schema/` | Modèles et exemples, description des onglets et colonnes |
| `POST …/{id_pg}/import-arborescence/validate/` puis `…/import-arborescence/` | Validation sans écriture (anomalies par onglet, ligne, colonne) puis import transactionnel |
| `POST …/{id_pg}/import-arborescence/validate-data/`, `…/import-data/` | Même chose à partir des données corrigées à l'écran (JSON, sans fichier) |
| `GET …/{id_pg}/import-arborescence/existing-summary/` | Contenu existant, pour confirmer un remplacement |
| `POST …/{id_pg}/import-actions/validate/`, `…/import-actions/` | Classeur des actions (actions, budget, ressources humaines) |
| `POST …/read-xlsx/` | Lecture brute d'un classeur quelconque |

L'import n'est possible que sur un plan en brouillon.

## Exports

Tous les exports renvoient un fichier (`Content-Disposition: attachment`) et sont réservés aux référents du plan et aux gestionnaires.

| Endpoint | Format |
|----------|--------|
| `GET …/{id_pg}/export-plan-docx/` | Fiche plan de gestion (Word) |
| `GET …/{id_pg}/export-arborescence-xlsx/`, `…/export-arborescence-presentation-xlsx/` | Arborescence au format d'import (réimportable) ou de présentation |
| `GET …/{id_pg}/export-fiches-actions-xlsx/`, `…/export-actions-xlsx/` | Fiches action ; classeur des actions au format d'import |
| `GET …/{id_pg}/export-budget-previsionnel-xlsx/`, `…/export-budget-suivi-xlsx/`, `…/export-rh-previsionnel-xlsx/`, `…/export-rh-suivi-xlsx/` | Budget et ressources humaines, prévisionnel et suivi |
| `POST …/{id_pg}/export-tableau-de-bord-xlsx/`, `…/export-suivi-actions-xlsx/` | Tableau de bord et suivi des actions, selon la vue et les filtres passés dans le corps |

## Exemple : créer un plan rattaché au rang précédent

```bash
curl -X POST https://<instance>/api/plans/plans/ \
  -H "Authorization: Bearer <access>" -H "Content-Type: application/json" \
  -d '{
    "nom_pg": "Plan de gestion 2027-2037 - Camargue",
    "annee_debut": 2027, "annee_fin": 2037, "rang": 3,
    "site_ids": [12], "plan_parent_id": 41
  }'
```

Le lien `plan_parent_id` n'est retenu que si le parent est de rang strictement inférieur et partage au moins un site ; sinon il est ignoré silencieusement. L'appelant devient référent du plan créé, sauf s'il est super administrateur ou rédacteur général (il a déjà tous les droits sur le plan).

## Référence interactive

<swagger-ui src="openapi/plans.json"/>
