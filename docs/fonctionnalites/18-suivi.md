# 18. Suivi des actions, Bilan et planification annuelle

Une fois le plan validé, la programmation est figée : le gestionnaire saisit chaque année ce qui a été **réalisé** et peut **ajuster** la planification de l'année. Le volet « Suivis » rassemble la saisie, le suivi des actions, le tableau de bord et le Bilan.

> Usage pas à pas : notice référent, [§ 4.9 Le suivi](../../documentation/docs/referent/suivi.md).

## Qui voit, qui saisit (#740)

| | Consulter | Saisir |
|---|---|---|
| Membres du plan, utilisateurs rattachés à un de ses sites | oui | non |
| Référents du plan, référents validés d'un site, admin de l'organisme gestionnaire, rédacteur principal, super admin | oui | oui |
| Rédacteur externe (#700) | non | non |

Le détail du plan expose `peut_voir_suivis` et `peut_saisir_suivis`. Côté serveur : `suivi_scope_q()` et `assert_suivi_access()` dans `apps/plans/access.py`, avec `lecture=True` pour les lectures.

Le suivi se saisit **plan validé** : c'est une donnée de suivi, pas une modification du plan.

## La saisie annuelle d'une action

Pour une année, `RealisationOperationAnnee` porte :

- le **niveau de réalisation** (terminé, partiel, en cours, reporté…), les opérateurs, le commentaire ;
- les **jours et le budget réalisés**, par organisme si la programmation l'est (`RealisationOperationAnneeOrganisme`) ;
- l'**emprise réalisée** (GeoJSON), comparée à l'emprise prévue sur la carte de la fiche de suivi ;
- les **montants par financeur** de l'année (`RealisationFinanceur`, financeur non prévu accepté).

Le suivi a ses propres réglages (#741, #760), qui valent par défaut ceux de la programmation : déclinaison par type de coût, saisie automatique du coût salarial, déclinaison par type de poste. Une action sans réglage ni suivi se voit proposer ceux du premier suivi saisi du plan (#761).

Un niveau de réalisation **global** sur la période se calcule (`Operation.compute_niveau_realisation_global()`) ou se fixe à la main.

Endpoints : `POST /api/plans/realisations/upsert/`, `…/realisations-organismes/upsert/`, `…/realisations/effacer/`, `…/realisations/suivi-reglages/{operation_id}/`.

## Planification annuelle ajustée (#794)

La programmation du plan reste la **référence**. Chaque année, le gestionnaire revoit chaque action et en ajuste l'année dans une **surcouche** (`AjustementAnnuel` et ses filles organismes / RH / financeurs). Pas de ligne = le plan.

- **Statuts** d'une année : planifiée, non prévue, reportée.
- **Report total** : l'année passe « reportée » et toute la suite est décalée d'autant. Une année qui a du réalisé ne bouge pas.
- **Report partiel** : l'année cible reçoit le reste à faire (prévu − réalisé).
- Enregistrer marque l'action **revue**, même sans changement.

Toutes les règles sont dans `apps/plans/planification_annuelle.py` (`Planification`) : ne pas les réécrire ailleurs. L'ajustement alimente le suivi des actions (colonnes Prévu PG / Prévu ajusté / Réalisé), la saisie, le Bilan et les exports.

API : `GET /api/plans/planification-annuelle/plan/{id}/?annee=`, `GET|PUT|DELETE …/operation/{id}/{annee}/`, `POST …/operation/{id}/{annee}/report/`.

## Les pages de lecture

| Page | Ce qu'elle montre |
|------|-------------------|
| **Suivi des actions** | Tableau par action et par année : icônes de réalisation, planification mensuelle, onglets Budget et RH (prévu PG, prévu ajusté, réalisé) |
| **Tableau de bord** | Vue synthétique de l'année |
| **Bilan** | Graphiques : budget, temps de travail, niveaux de réalisation, indicateurs d'état et de pression, évolution par année |

### Le Bilan

- Endpoints : `/api/plans/realisations/bilan/{plan_id}/`, `…/bilan-indicateurs/{plan_id}/`, `…/bilan-series/{plan_id}/`.
- **Filtres** partagés (#753), règles dans `apps/plans/bilan_filtres.py` : enjeux (choix multiple, par les deux branches de l'arborescence), organisme (seule sa part de budget et de temps), types d'indicateurs.
- Le prévu est celui de la **planification ajustée** ; une action compte dans la catégorie de son **type principal**.
- Graphiques : bibliothèque maison `frontend/src/app/shared/components/charts/` (donut, barres, courbes, radar).

## Exports liés

Fiches de suivi d'une année, suivi budgétaire et suivi RH, planification annuelle : voir [19. Exports et imports](19-exports-imports.md).
