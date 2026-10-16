# Arborescence d'un plan

Le contenu d'un plan suit la méthode CT88 : **enjeux** (et facteurs clés de réussite) → **facteurs d'influence** → **pressions** ; **objectifs à long terme** → **niveaux d'exigence** → **indicateurs d'état** → **métriques** ; **objectifs opérationnels** → **résultats attendus** → **indicateurs de pression** → **métriques**. Les actions se rattachent aux indicateurs et aux métriques ([Actions et suivi](actions-suivi.md)).

Chaque niveau a son ViewSet, sur le même modèle :

| Niveau | Préfixe | Endpoints « par parent » |
|--------|---------|--------------------------|
| Enjeux et FCR | `/api/plans/enjeux/` | `by-plan/{plan_id}/` (renvoie aussi `plan_statut`), `stats/` |
| Documents du patrimoine géologique | `/api/plans/enjeux-fichiers/` | `{id}/download/` |
| Facteurs d'influence | `/api/plans/facteurs-influence/` | `by-enjeu/{enjeu_id}/`, `by-plan/{plan_id}/` (candidats au lien) |
| Pressions | `/api/plans/pressions/` | `by-facteur/{facteur_id}/` |
| Objectifs à long terme | `/api/plans/objectifs-long-terme/` | `by-enjeu/{enjeu_id}/` |
| Niveaux d'exigence | `/api/plans/niveaux-exigence/` | `by-olt/{olt_id}/` |
| Objectifs opérationnels | `/api/plans/objectifs-operationnels/` | `by-pression/{pression_id}/`, `by-plan/{plan_id}/` |
| Résultats attendus | `/api/plans/resultats-attendus/` | `by-oo/{oo_id}/` |
| Indicateurs | `/api/plans/indicateurs/` | `by-ne/{ne_id}/`, `by-ra/{ra_id}/`, `{id}/global/` |
| Métriques | `/api/plans/metriques/` | `by-indicateur/{indicateur_id}/` |
| Mesures (valeurs saisies) | `/api/plans/mesures/` | `by-metrique/{metrique_id}/` |
| Saisie annuelle de l'indicateur | `/api/plans/indicateur-mesures/` | `upsert/`, `resolved/`, `auto-score/`, `global-evaluation/{indicateur_id}/` |

## Opérations communes

- **`POST …/reorder/`** sur chaque niveau : `{ "parent_id": …, "ordered_ids": [...] }` réordonne les enfants d'un parent, ce qui recalcule la numérotation automatique.
- **`POST …/{id}/move/`** (pressions, indicateurs, actions) : déplace un élément vers un autre parent.
- **Lier / copier / détacher** (`link/`, `copy/`, `unlink/`) sur les facteurs d'influence, objectifs opérationnels, résultats attendus et indicateurs : un élément lié reste unique et s'affiche sous plusieurs parents ; une copie est un duplicata indépendant. `duplicate/` joue ce rôle pour un indicateur.
- **Espèces et habitats** d'un enjeu : `POST …/enjeux/{id}/add_taxon/` (`cd_nom` TaxRef), `DELETE …/remove_taxon/{cd_nom}/`, `add_habitat/` (`cd_hab` HabRef), `remove_habitat/{cd_hab}/`. Les référentiels se consultent dans [Référentiels](referentiels.md).
- **Numéro fixé** : chaque élément numéroté accepte un `numero_fixe` qui gèle son numéro ; les autres sautent cette valeur.

## Métriques et scores

Une métrique porte un type de grille (`intervalle`, `chiffre`, `texte`, `indetermine`), ses seuils (score de 1 à 5, niveaux désactivables) et, pour une grille « intervalle », des **blocs** combinés par ET / OU. Le score d'un indicateur pour une année est la moyenne pondérée des scores de ses métriques ; `indicateur-mesures/resolved/` renvoie le score effectif (calculé ou surchargé manuellement avec justification), `global-evaluation/` l'évaluation sur toute la période.

## Règles d'accès

- Lecture : tout utilisateur lié au plan, plus la lecture d'exploration pour les plans validés (réponse élaguée des mesures).
- Écriture : référents du plan uniquement, et seulement quand le plan est en brouillon (`403` sinon). La suppression d'un élément supprime tout ce qui lui est rattaché.

## Référence interactive

<swagger-ui src="openapi/arborescence.json"/>
