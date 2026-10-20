# Actions et suivi

Une **action** (`Operation`, clé `id_operation`) est rattachée à un ou plusieurs indicateurs et métriques, porte un type GestRef, une programmation par année (jours, budget, mois, sites, opérateurs, financeurs) selon un **mode de ventilation**, et, pour un inventaire ou un suivi, un protocole. Le **suivi** enregistre, par année, la réalisation, les jours et budgets consommés.

## Actions

| Endpoint | Rôle |
|----------|------|
| `GET/POST /api/plans/operations/` | Liste (filtres : plan, enjeu, type, priorité, année, organisme, statut de réalisation…) et création |
| `GET/PUT/PATCH/DELETE /api/plans/operations/{id_operation}/` | Détail (programmation complète, `geom` en GeoJSON), modification, suppression |
| `GET …/by-plan/{plan_id}/`, `…/by-indicateur/{indicateur_id}/` | Actions d'un plan (groupées par type) ou d'un indicateur |
| `POST …/{id}/add-metrique/`, `…/remove-metrique/`, `…/create-indicator/` | Liens avec les métriques ; création d'un indicateur de réponse |
| `POST …/{id}/move/`, `…/copy/`, `POST …/reorder/` | Déplacer, copier, réordonner |
| `GET …/ventilation-defaults/{plan_id}/` | Mode de ventilation et réglages budgétaires de la dernière action saisie, proposés par défaut à une nouvelle action |
| `GET …/{id}/export-fiche-xlsx/` | La fiche de cette seule action (Excel) |
| `GET/POST /api/plans/postes/`, `GET …/by-plan/{plan_id}/`, `GET/POST /api/plans/fonctions/` | Postes (ressources humaines) du plan et fonctions types |

### Mode de ventilation

`ventilation_mode` fixe le niveau de détail de la programmation : `none`, `by_org`, `by_type`, `by_org_type`, `by_type_poste`, `by_org_type_poste`. Dès que le mode intègre le type de budget, deux réglages s'ajoutent : `declinaison_par_type_cout` (détail salarial, stage, prestataire, autres) et `cout_salarial_auto` (coût salarial = jours × coût jour des postes, proposé par les deux modes « par type de poste »). Les totaux d'un plan sont identiques quel que soit le mode : seule la finesse du stockage change.

### Brouillon d'action

Une action peut être enregistrée sans validation des champs obligatoires (`statut_saisie: brouillon`) puis complétée par `PATCH`.

## Suivi

| Endpoint | Rôle |
|----------|------|
| `GET/POST /api/plans/realisations/`, `POST …/upsert/` | Réalisation annuelle d'une action : niveau, opérateurs et financeurs effectifs, jours et budget réalisés, commentaire, emprise |
| `GET …/by-operation/{operation_id}/`, `…/by-plan/{plan_id}/` | Réalisations d'une action ou de tout un plan |
| `POST …/effacer/` | Revenir à l'état « non renseigné » pour une année |
| `GET/POST/DELETE …/global-realisation/{operation_id}/` | Réalisation globale sur la période, calculée ou forcée manuellement |
| `/api/plans/realisations-organismes/`, `…/upsert/` | Ventilation par organisme du réalisé |
| `GET …/bilan/{plan_id}/`, `…/bilan-indicateurs/{plan_id}/`, `…/bilan-series/{plan_id}/` | Agrégations du **Bilan de la gestion** : budget et jours prévus / réalisés, taux de réalisation, répartition des scores, séries par année ; filtrables par `?enjeu_id=` et par portée (global, mi-parcours, annuel) |

Le suivi n'est saisissable que sur un plan `valide` ou `modifie`, par ses référents et les gestionnaires. Les membres du plan et les utilisateurs rattachés à l'un de ses sites le consultent en lecture seule (méthodes `GET`). Le détail du plan l'indique avec `peut_voir_suivis`, `peut_saisir_suivis` et `peut_exporter`. Un rédacteur externe n'y accède jamais.

## Inventaires et suivis scientifiques

| Endpoint | Rôle |
|----------|------|
| `GET/POST /api/inventaires/suivis/` | Suivis et inventaires, inscrits ou non dans un plan : type, objectifs, cibles, statut, fréquence, protocoles (standardisés ou libres), bancarisation |
| `GET/PUT/PATCH/DELETE /api/inventaires/suivis/{id_suivi_inventaire}/` | Détail et modification |

Un suivi créé ici peut ensuite être rattaché à une action de suivi d'un plan (`id_suivi_inventaire` sur l'action). Les protocoles standardisés viennent du catalogue CAMPanule ([Référentiels](referentiels.md)).

## Référence interactive

<swagger-ui src="openapi/actions-suivi.json"/>
