# 16. Arborescence d'un plan de gestion

L'arborescence est le cœur d'un plan : elle relie ce que l'on veut préserver (les enjeux) à ce que l'on fait (les actions) et à ce que l'on mesure (les indicateurs).

> Usage pas à pas : notice référent, [§ 4.5 Les enjeux](../../documentation/docs/referent/enjeux.md), [§ 4.6 Indicateurs et métriques](../../documentation/docs/referent/indicateurs-metriques.md), [tableau d'arborescence](../../documentation/docs/referent/tableau-arborescence.md).

## Les deux branches

```
                         Plan de gestion
                    ┌──────────┴───────────┐
            Enjeu (état)          Facteur clé de réussite (FCR)
                 │                         │
   Objectif à long terme (OLT)   Facteur d'influence → Pression
                 │                         │
     Niveau d'exigence (NE)      Objectif opérationnel (OO)
                 │                         │
   Indicateur d'état → Métriques  Résultat attendu (RA)
                                           │
                                 Indicateur de pression → Métriques
                 └──────────────┬──────────┘
                             Actions
```

| Niveau | Modèle | Rôle |
|--------|--------|------|
| Enjeu / FCR | `Enjeu` (catégorie `ENJEU` ou `FCR`, `is_enjeu()` / `is_fcr()`) | Ce que le plan protège, ou ce qui conditionne sa réussite |
| Facteur d'influence, pression | `FacteurInfluence`, `Pression` | Ce qui agit sur l'enjeu (pressions typées PressRef) |
| OLT, NE | `ObjectifLongTerme`, `NiveauExigence` | État visé à long terme et seuil mesurable |
| OO, RA | `ObjectifOperationnel`, `ResultatAttendu` | Réponse opérationnelle à une pression, et résultat attendu |
| Indicateur | `Indicateur` (`type_indicateur` : ÉTAT, PRESSION, RÉPONSE) | Ce que l'on suit |
| Métrique, mesure | `Metrique`, `Mesure` | La grandeur et ses valeurs datées |

Les liens transverses sont des tables `Cor…` : un facteur ou un OO peut servir plusieurs enjeux (`CorFacteurEnjeu`, `CorOoEnjeu`), un OO répond à des pressions (`CorOoPression`). Un OO de FCR relié à aucune pression déclenche une alerte persistante dans « Stratégie opérationnelle » (#731).

Un enjeu porte aussi ses taxons (TaxRef), habitats (HabRef), objets géologiques et documents (`CorEnjeu…`).

## Métriques et grilles de scores

- Une métrique a un **format** (valeur simple ou grille, nomenclature `FORMAT_METRIQUE`), une unité, un sens de variation et un état de référence.
- Sa **grille de scores** (`MetriqueScoreBlock`) range une valeur dans l'un des niveaux « Très mauvais » à « Très bon ». Les règles de la grille sont centralisées dans `apps/plans/grille_metrique.py` (`erreurs_grille()`), utilisées par le serializer et l'import.
- Les indicateurs de **réponse** se rattachent aux actions et se saisissent dans leur fiche ; ils ne comptent pas dans le Bilan des indicateurs.

## Codes affichés

Les enjeux, FCR, OLT, OO et actions ont un code calculé (« Enjeu 2 », « FCR 1 », « CS3 »…) d'après leur rang dans le plan. Les actions prennent le préfixe de leur catégorie d'action réserve, sinon de leur type d'action ; le numéro peut être fixé à la main (`numero_manuel`).

## Lecture et écriture

- Tout utilisateur lié au plan lit toute l'arborescence (#610), un plan validé s'ouvre en lecture d'exploration à tout utilisateur connecté, sans données sensibles (#683).
- Seuls les référents du plan et les gestionnaires écrivent, et **seulement en brouillon** (#248). Voir [23. Rôles et droits](23-droits.md).
- Le périmètre de lecture est centralisé dans `apps/plans/access.py` (`scope_by_plan()`), à réutiliser dans tout nouveau ViewSet.

## Copier, lier, importer

- **Copier** une branche ou un élément vers un autre endroit du plan : `ElementCopyService` (`apps/plans/element_copy.py`).
- **Nouvelle version** du plan : tout le contenu est copié (`PlanDuplicationService.copy_content()`, voir [14. Plans](14-plans.md)).
- **Import Excel** de l'arborescence et réimport : voir [19. Exports et imports](19-exports-imports.md).
