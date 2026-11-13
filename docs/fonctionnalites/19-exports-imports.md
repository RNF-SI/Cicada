# 19. Exports et imports d'un plan

> Usage pas à pas : notice référent, [§ 4.12 Les exports](../../documentation/docs/referent/exports.md) et [§ 4.3.2 Importer un plan depuis Excel](../../documentation/docs/referent/parametrage.md#432-importer-un-plan-depuis-un-fichier-excel).
> Format détaillé des classeurs d'import : [IMPORT_PLANS_GUIDE.md](../IMPORT_PLANS_GUIDE.md).

## Qui peut exporter

Un export extrait **tout** le contenu du plan, au-delà de la consultation. Il est réservé aux **référents du plan** et aux gestionnaires (admin organisme, rédacteur principal, super admin).

- Serveur : `PlanGestionViewSet._can_export_plan()` / `_get_plan_for_export()` (403 sinon). Le détail du plan expose `peut_exporter`.
- Écran : la page « Exports » et le bouton « Générer » des pages du plan (#795) ne s'affichent qu'à ces utilisateurs.
- Les classeurs **exemples** (`example-*-xlsx`) restent ouverts à tout utilisateur connecté.

## Les exports

| Export | Endpoint (`/api/plans/plans/{id}/…`) | Module |
|--------|--------------------------------------|--------|
| Fiche plan de gestion (Word) | `export-plan-docx/` | `services_export_word.py` |
| Arborescence (présentation) | `export-arborescence-presentation-xlsx/` | `services_export_arbo.py` |
| Contenu du plan (réimportable) | `export-arborescence-xlsx/` | `services_import.py` |
| Fiches action (Excel / Word) | `export-fiches-actions-xlsx/`, `-docx/` | `services_export_fiche_action.py`, `…_word.py` |
| Budget et RH, prévisionnel et suivi | `export-budget-previsionnel-xlsx/`, `export-budget-suivi-xlsx/`, `export-rh-…` | `services_export_budget_rh.py` |
| Fiches de suivi d'une année | `export-fiches-suivi-xlsx/?annee=` | `services_export_fiche_suivi.py` |
| Planification annuelle d'une année | `export-planification-annuelle-xlsx/?annee=` | `services_export_planification_annuelle.py` |
| Actions (réimportable) | `export-actions-xlsx/` | `services_import_actions.py` |

Une seule action : `GET /api/plans/operations/{id}/export-fiche-xlsx/`, `export-fiche-docx/`, `export-fiche-suivi-xlsx/?annee=`.

### Règles communes

- **Les exports ne recalculent pas à leur façon.** Budget et RH passent par `services_export_finance.py` (`build_action_finance()`), le même calcul que le Bilan. Les fiches action Excel et Word partagent leurs fonctions de données (`actions_a_exporter()`, `financeurs_rows()`, `code_referentiel()`…).
- Les colonnes suivent la ventilation **la plus détaillée** des actions du plan (`PlanFinance`).
- Le suivi budgétaire et RH a trois colonnes par année : prévu du plan, prévu ajusté, réalisé (#794).

## Les imports

Deux classeurs, à importer dans un plan **en brouillon**, dans cet ordre :

1. **Contenu du plan** (arborescence) : enjeux, objectifs, indicateurs, métriques et grilles de scores (format 1.1, #787). Les mesures ne font pas l'aller-retour.
2. **Actions** (#786) : toute la programmation de chaque action, dans un plan **sans action**, sur cette instance ou une autre.
   - Les références se retrouvent **par leur nom** (indicateur, organisme, métrique, site par code INPN) ; un poste absent est créé.
   - Le type d'action s'écrit `CODE — libellé`. Un type d'une version antérieure du référentiel est converti selon la table de correspondance (#786, retour 09/11).
   - Seule la **programmation** voyage, pas le réalisé.

Chaque import passe par une **validation** (rapport d'erreurs et d'avertissements) avant l'exécution.

## Import en masse de sites

Voir [15. Import en masse](15-import-masse.md).
