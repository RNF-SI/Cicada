# 17. Actions de gestion et programmation

Une action (`Operation`) décrit ce que le gestionnaire fait pour atteindre un objectif : son type, son calendrier, son budget, le temps de travail et, pour une action de connaissance (CS), son suivi.

> Usage pas à pas : notice référent, [§ 4.8 Les actions de gestion](../../documentation/docs/referent/actions.md).
> Règles de calcul détaillées : section « Plans « Ventilation — … » » du `CLAUDE.md`.

## Ce que porte une action

| Bloc | Champs principaux |
|------|-------------------|
| Rattachement | `id_indicateur` et/ou métriques (`CorOperationMetrique`) |
| Classement | type d'action GestRef (`id_type_action`), types complémentaires (#792), catégorie d'action réserve CT88, priorité |
| Description | libellé, description, action de restauration, sites (`CorOperationSite`), emprise (GeoJSON, WGS 84) |
| Calendrier | années (`annee_min` → `annee_max`), mois programmés, fréquence |
| Programmation | budget et temps de travail par année (`OperationAnnee`) ou pour toute la période (programmation globale, #735) |
| Acteurs | opérateurs, partenaires, financeurs avec montant (#790) |
| Suivi | pour une action CS : suivi / inventaire (`SuiviInventaire`) et protocoles |

## Type d'action

- **Type principal** : un type du référentiel GestRef en service (versionné, voir [20. Référentiels](20-referentiels.md)). Il donne le préfixe du code (CS, IP…) si aucune catégorie réserve n'est choisie, et sert au Bilan, aux totaux et aux exports par catégorie.
- **Types complémentaires** (#792) : facultatifs, affichés sur la fiche et dans les exports, trouvés par l'exploration. Avec au moins un type complémentaire, le libellé devient obligatoire.
- **Suivi** : une action porte un suivi dès qu'**un** de ses types est CS (`Operation.type_de_suivi()`). Le suivi est partagé avec le module Inventaires (#715) : la fiche action fait référence.

## Ventilation du budget et du temps de travail

Le **mode de ventilation** (`Operation.ventilation_mode`) fixe la forme du tableau de programmation :

| Mode | Budget | Temps de travail |
|------|--------|------------------|
| `none` — aucune ventilation | un total par année | un seul temps total par année (#759) |
| `by_org` — par organisme | par organisme gestionnaire | par organisme |
| `by_type` — par type de budget | fonctionnement / investissement | — |
| `by_org_type` | organisme × type de budget | par organisme |
| `by_type_poste` | type de budget, coûts détaillés | par poste |
| `by_org_type_poste` | organisme × type de budget, coûts détaillés | par poste et organisme |

Trois réglages s'y ajoutent :

- **Déclinaison par type de coût** (`declinaison_par_type_cout`) : coût salarial, stage, prestataire, autres coûts, au lieu des seules enveloppes.
- **Déclinaison par type de poste** (`declinaison_par_poste`, #773) : temps de travail saisi par poste.
- **Saisie automatique du coût salarial** (`cout_salarial_auto`) : jours × coût jour du poste, sinon saisi.

Sans type de budget, ni le budget ni le temps ne distinguent fonctionnement et investissement.

**Source de vérité des calculs** : `frontend/src/app/shared/utils/operation-budget.ts` côté écran, `backend/apps/plans/services_export_finance.py` côté exports et Bilan. Toute règle se corrige des deux côtés.

À la création, le formulaire reprend le paramétrage de la dernière action du plan (#641).

## Programmation annuelle ou globale

- **Annuelle** (par défaut) : une ligne `OperationAnnee` par année, avec ses organismes et lignes de temps.
- **Globale** (#735) : budget et temps saisis une fois pour la période, sur une ligne sans année. Le gestionnaire par défaut `OperationAnnee.objects` **exclut** cette ligne ; utiliser `OperationAnnee.tous` pour la lire.

La programmation se met à jour **en place** : ne jamais supprimer puis recréer les années, le suivi saisi partirait en cascade.

## Postes, RH et financeurs

- **Postes** (`Poste`) : propres au plan, avec organisme, coût jour, fonctions et type de poste. Page « Postes / RH / Financeurs ».
- **Financeurs** (`Financeur`, #790) : propres au plan, nom + catégorie. Montant **prévu global** par action, **réalisé annuel** au suivi. La somme est comparée au budget prévu (alerte, jamais bloquante), calcul unique dans `apps/plans/financeurs.py`.

## Enregistrer sans valider

Le bouton « Enregistrer » (#251) sauve sans contrôler les champs obligatoires et reste sur le formulaire ; « Valider » applique toutes les règles.

## API

- `GET/POST /api/plans/operations/`, `PATCH /api/plans/operations/{id}/`
- `GET /api/plans/operations/ventilation-defaults/{plan_id}/`
- `POST /api/plans/operations/{id}/actualiser-type/` (type à actualiser après un passage de référentiel)

Référence complète : page API « Actions et suivi » du site de documentation.
