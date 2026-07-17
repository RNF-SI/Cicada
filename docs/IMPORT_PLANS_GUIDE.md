# Import Excel d'un plan de gestion (V1, sans IA)

Ce guide décrit l'import d'un plan de gestion à partir de classeurs Excel
(`.xlsx`), en **deux modules complémentaires** :

1. **Arborescence** — enjeux, facteurs, pressions, objectifs, indicateurs,
   métriques ;
2. **Actions** — opérations rattachées aux indicateurs, avec budgets et temps
   de travail (RH).

L'import remplit un **plan de gestion en brouillon**. Il est réservé aux
gestionnaires du plan (référent, admin organisme, super admin) et bloqué hors
brouillon par la permission `CanModifyOnlyDraftPlan`.

Backend : `apps/plans/services_import.py` (arborescence) et
`apps/plans/services_import_actions.py` (actions).
Frontend : section « Import / export » de la page **Paramètres du plan**
(`plan-settings.component`).

---

## Principe général

- Le classeur est **multi-onglets**, un onglet par niveau de l'arborescence.
- Chaque ligne porte un **code logique** libre choisi par le rédacteur (`E1`,
  `F1`, `P1`, `I1`…). Les rattachements se font en reportant le code du parent
  dans une colonne dédiée. Les liens N-N (un facteur partagé entre plusieurs
  enjeux, un OO rattaché à plusieurs pressions) s'expriment en **cellules
  multi-valeurs** séparées par des virgules (`E1,E3`).
- **Listes déroulantes de rattachement** : les colonnes de code parent proposent
  la liste des codes de l'onglet cible (ex : la colonne `enjeux` d'un facteur
  propose tous les codes de l'onglet `Enjeux` ; la colonne `action` des onglets
  `Budgets`/`RH` propose les codes de l'onglet `Actions`). La liste se met à jour
  au fur et à mesure. Pour les colonnes multi-valeurs, la liste est une aide
  non bloquante (on peut saisir plusieurs codes séparés par des virgules).
- Un onglet `Listes` **masqué** alimente les listes déroulantes des colonnes de
  nomenclature (catégorie, type, priorité…).
- **Ligne exemple** : le modèle vierge contient, dans chaque onglet de saisie,
  une première ligne grisée dont la 1re colonne vaut `(exemple)`. Elle montre
  quoi écrire et **n'est jamais importée** (ignorée au parsing). On peut la
  laisser, la remplacer ou la supprimer.
- **Exemples complets téléchargeables** : deux classeurs pédagogiques fictifs et
  entièrement remplis (arborescence et actions) illustrent tous les onglets et
  leurs liens. Indépendants d'un plan, accessibles via un bouton dédié.
- **Onglets de référence non modifiables** : dans le classeur d'actions, les
  onglets `Indicateurs`, `Postes` et `Listes` sont protégés (lecture seule) pour
  éviter de corrompre les identifiants techniques.
- **Validation des taxons / habitats contre les référentiels** : `cd_nom` est
  vérifié dans TaxRef et `cd_hab` dans HabRef. Si le code est absent mais le
  **nom** est renseigné (ou, pour un habitat, le **code typologique** type
  « 7110 »), le bon code est **retrouvé automatiquement** et signalé par un
  avertissement ; un code introuvable ou ambigu est une erreur. La validation
  est neutralisée si le référentiel n'est pas chargé en base.
- **Correction interactive (#9)** : après validation, les données sont éditables
  dans une grille (cellules en erreur surlignées). On corrige, on **revalide**
  (`validate-data`) et on **importe** (`import-data`) sans repasser par Excel.
- **Import « mapping » (#10)** : téléverser un fichier Excel de structure
  **quelconque**, `read-xlsx` en lit les onglets/colonnes, l'utilisateur associe
  ses colonnes au format cible. *Fonctionnel en backend mais présenté « Prochainement »
  côté UI (désactivé) en attendant des formats réels d'utilisateurs.*
- **Trois modes d'import** (paramètre `mode`) sur un plan qui a déjà du contenu :
  - `create` (défaut) : refuse un plan non vide ;
  - `add` : **ajoute** sans toucher à l'existant (refuse un libellé d'enjeu déjà présent) ;
  - `replace` : **supprime** l'arborescence existante (les deux branches +
    opérations/budgets/RH/suivis en cascade) puis recrée — **destructif**,
    confirmation forte côté UI (modale listant ce qui sera perdu).
- La page **Paramètres du plan** présente l'import en **parcours guidé** (3 étapes
  numérotées + « Comment ça marche ? » dépliable + options avancées repliées).
- Le module **actions** a aussi son explication : le classeur embarque déjà les
  indicateurs/postes du plan (onglets de référence non modifiables).
- Deux temps : **valider** (dry-run, aucun écrit) puis **importer** (transaction).

---

## Module 1 — Arborescence

Onglets : `Lisez-moi`, `Enjeux`, `Facteurs`, `Pressions`, `OLT`, `NE`, `OO`,
`RA`, `Indicateurs`, `Metriques`, `Taxons`, `Habitats`, `Listes` (masqué).

Structure représentée :

```
Enjeu → OLT → Niveau d'exigence → Indicateur (état) → Métrique
Enjeu → Facteur → Pression → Objectif opérationnel → Résultat attendu
      → Indicateur (pression/réponse) → Métrique
```

Un **FCR** relie directement l'enjeu à ses objectifs opérationnels (sans facteur
ni pression) : renseignez la colonne `enjeu` de l'onglet `OO`, en laissant
`pressions` vide.

Points d'attention :

- `Enjeux` : `libellé` unique par plan, `intitulé court` ≤ 25 caractères,
  `catégorie` obligatoire (Enjeu / FCR). Les types écologiques et socio-éco sont
  des colonnes **multi-valeurs**.
- `Indicateurs` : le parent est **soit** un niveau d'exigence (`N…`) **soit** un
  résultat attendu (`R…`) — jamais les deux.
- `Metriques` : seul le libellé est importé ; l'indicateur reste
  « indéterminé » (aucune grille de scoring en V1).
- `Taxons` / `Habitats` : rattachés à un **enjeu** (`E…`) ou un **indicateur**
  (`I…`) via la colonne `cible`. `cd_nom` (taxon) est un entier obligatoire,
  `cd_hab` (habitat) est obligatoire ; le nom est facultatif (repris du
  référentiel INPN à l'affichage).

---

## Module 2 — Actions

Le classeur d'actions est **généré depuis le plan** (les indicateurs et postes
existants y sont listés en référence, avec un code et un identifiant technique) :

Onglets : `Lisez-moi`, `Indicateurs` (référence), `Postes` (référence),
`Listes` (masqué), `Actions`, `Budgets`, `RH`.

- `Actions` — une action par ligne : `code`, `indicateur` (code de référence),
  `libellé`, `type d'action`, `priorité`, `année début` / `année fin`,
  `opérateurs`, `financeurs`. Les années créent la programmation annuelle
  (`OperationAnnee`). Les actions sont importées en **brouillon**.
- `Budgets` (facultatif) — budget de fonctionnement / investissement par
  `(action, année)`. Bascule l'opération en `ventilation_mode = 'by_type'`.
- `RH` (facultatif, #560) — temps de travail en `jours` par
  `(action, année, poste)`, avec `financé ? (Oui/Non)`. Crée des
  `OperationAnneeRH` et active `declinaison_par_poste`. Les postes doivent
  exister au préalable (page « Postes / RH » du plan) pour être référencés.

Une année de budget/RH hors de la période déclarée de l'action génère un
**avertissement** (non bloquant) et l'année est créée automatiquement.

---

## Endpoints API

Toutes les routes sont des actions du `PlanGestionViewSet`
(`/api/plans/plans/{id}/…`) et exigent l'authentification. Les écritures sont
bloquées hors brouillon.

| Méthode | URL | Rôle |
|--------|-----|------|
| `GET` | `example-arborescence-xlsx/` | **Exemple** complet d'arborescence (indépendant d'un plan) |
| `GET` | `example-actions-xlsx/` | **Exemple** complet d'actions (indépendant d'un plan) |
| `GET` | `export-arborescence-xlsx/` | Classeur arborescence (pré-rempli). `?empty=1` = modèle vierge (avec ligne exemple) |
| `POST` | `import-arborescence/validate/` | Validation (dry-run), renvoie le rapport |
| `POST` | `import-arborescence/` | Import de l'arborescence (transaction) |
| `GET` | `export-actions-xlsx/` | Classeur actions (indicateurs/postes en référence) |
| `POST` | `import-actions/validate/` | Validation (dry-run) des actions |
| `POST` | `import-actions/` | Import des actions + budgets + RH (transaction) |

Les `POST` d'import attendent un `multipart/form-data` avec un champ `file`
(le classeur `.xlsx`).

### Format du rapport de validation

```json
{
  "can_import": true,
  "n_errors": 0,
  "n_warnings": 1,
  "issues": [
    { "sheet": "Budgets", "row": 5, "column": "annee",
      "level": "warning", "message": "L'année 2099 est hors de la période…" }
  ],
  "summary": { "enjeux": 9, "indicateurs": 32, "metriques": 32 }
}
```

En cas d'échec de validation à l'exécution, l'endpoint d'import renvoie **400**
avec ce même rapport dans le corps.

### Réponse d'un import réussi

```json
{ "created": { "actions": 6, "annees": 18, "budgets": 4, "rh": 12 }, "total": 6 }
```

---

## Tests

- `backend/tests/apps/plans/test_import_arborescence.py` (23 tests) — logique
  arborescence : build, aller-retour, facteur partagé #552, FCR direct, XOR
  indicateur (état/réponse), taxons/habitats, flags types d'enjeu, **listes
  déroulantes inter-onglets**, **ligne exemple ignorée**, **exemple complet**,
  validations.
- `backend/tests/apps/plans/test_import_actions.py` (23 tests) — actions,
  budgets, RH, **dropdown action des onglets Budgets/RH**, **ligne exemple
  ignorée**, **exemple complet**.
- `backend/tests/apps/plans/test_import_endpoints.py` (11 tests) — couche HTTP :
  export (tout statut, MIME), validation multipart, import réel, **verrou
  brouillon (403 hors draft)**, **endpoints exemple**, authentification, fichier
  manquant.
- `frontend/e2e/tests/features/import-plan.spec.ts` (3 tests E2E) — round-trip
  d'import par l'UI, verrou brouillon, **téléchargement des exemples**.
- `frontend/src/app/core/services/admin.service.spec.ts` (méthodes d'import)
- `frontend/e2e/tests/features/import-plan.spec.ts` (2 tests E2E Playwright) —
  round-trip **par l'interface** : export du classeur pré-rempli d'un plan
  seedé → import dans un brouillon vide via la page « Paramètres du plan » →
  vérification de l'arborescence créée ; + verrou brouillon (upload masqué sur
  un plan validé). Le fichier Excel est produit à la volée par l'export (pas de
  fixture binaire committée).

```bash
# Backend
docker compose exec web pytest tests/apps/plans/test_import_arborescence.py \
                                tests/apps/plans/test_import_actions.py \
                                tests/apps/plans/test_import_endpoints.py
# E2E (stack lancée + seed ; voir docs/TESTING.md)
cd frontend && npm run e2e -- e2e/tests/features/import-plan.spec.ts
```

---

## Limites connues (V1)

- Pas de grille de scoring des métriques (indicateur « indéterminé »).
- Responsabilités (site/organisme) non gérées dans l'arborescence.
- Budget par organisme (`OperationAnneeOrganisme`) non géré (seulement la
  ventilation fonctionnement / investissement globale).
- Pas de suivis / inventaires ni de protocoles CAMPanule.
