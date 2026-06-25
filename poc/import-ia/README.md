# POC — Import IA de plans de gestion existants (#478)

Proof of concept pour l'intégration de **plans de gestion textuels existants** (PDF
hétérogènes) dans Cicada. **Branche `poc/import-plans-ia` — rien n'est câblé dans
l'application qui tourne.**

Suivant la piste de l'issue #478 (« deux modules séparés : arborescence puis actions »),
le POC est découpé en **deux modules** autour d'un **format intermédiaire JSON relisible** :

```
 PDF (tome II / tome III, hétérogènes)
        │  (1) extraction LLM multimodale
        ▼
   JSON normalisé  ──►  [relecture / correction humaine]  ──►  import en base
        │                                                         │
        ├─ module ARBORESCENCE : enjeux → OLT → NE → indicateurs → métriques
        └─ module ACTIONS      : fiches actions → Operations, rattachées aux indicateurs
```

> Décision de périmètre : on importe **arborescence + libellés de métriques** et
> **fiches actions**, mais **pas les valeurs/grilles de scoring des métriques**
> (l'indicateur reste « indéterminé » faute de mesures). L'objectif n'est pas
> l'automatisation totale mais de passer de **~3 jours à ~½ journée** par plan :
> l'IA produit un brouillon à 80-90 % qu'un gestionnaire corrige.

## Fichiers

| Fichier | Rôle |
|---|---|
| `cicada_fiche_action_schema.json` | Schéma cible **actions** (aligné sur l'export Cicada "Fiche action"). |
| `cicada_arborescence_schema.json` | Schéma cible **arborescence** (enjeux/FCR/pressions/OLT/NE/indicateurs/métriques). |
| `extract_fiches.py` | (1-actions) PDF → JSON via l'API Claude (sortie structurée, anti-hallucination). |
| `json_to_excel.py` | (2-actions) JSON → classeur Excel au format du modèle Cicada (1 onglet/fiche). |
| `poc_import_fiches.py` | (3-actions) commande Django : JSON → `Operation` brouillon, rattachée aux indicateurs. |
| `poc_import_arborescence.py` | (3-arborescence) commande Django : JSON → Enjeu/OLT/NE/Indicateur/Métrique. |
| `templates/modele_export_fiche_action.xlsx` | Modèle d'export Cicada de référence. |
| `sample_output/extraction_demo.json` | 6 fiches réelles extraites (Val Suzon + Mépieu), validées. |
| `sample_output/arborescence_demo.json` | Arborescence réelle extraite (Val Suzon, Enjeu 2 / falaises), validée. |
| `sample_output/arborescence_aligned_demo.json` | Petite arborescence alignée sur les 6 fiches (test du rattachement). |
| `sample_output/fiches_remplies.xlsx` | Sortie (2-actions) générée à partir de la démo. |

## Utilisation

### (1) Extraction PDF → JSON  *(nécessite une clé API Anthropic, distincte de l'abonnement Max)*
```bash
pip install "anthropic>=0.92" jsonschema pypdf
export ANTHROPIC_API_KEY=sk-ant-...
python extract_fiches.py "tome_iii.pdf" --pages 17-40 --out fiches.json
```
L'extraction de l'arborescence (tome II) suit le même principe avec
`cicada_arborescence_schema.json` (script analogue ; les démos `sample_output/*.json`
ont été produites via Claude Code, sans clé).

### (2) JSON actions → Excel  *(relecture humaine)*
```bash
pip install openpyxl
python json_to_excel.py sample_output/extraction_demo.json -o sample_output/fiches_remplies.xlsx
```

### (3) Import en base  *(commandes Django — DRY-RUN par défaut)*
```bash
# Copier les commandes dans l'arbre de l'app UNIQUEMENT pour tester :
mkdir -p backend/apps/plans/management/commands
touch backend/apps/plans/management/__init__.py backend/apps/plans/management/commands/__init__.py
cp poc/import-ia/poc_import_arborescence.py poc/import-ia/poc_import_fiches.py \
   backend/apps/plans/management/commands/

# 1. l'arborescence d'abord (crée les indicateurs)
docker compose exec web python manage.py poc_import_arborescence \
   /tmp/arbo.json --plan <ID_PLAN> --user admin@test.fr
# 2. puis les actions (se rattachent aux indicateurs créés)
docker compose exec web python manage.py poc_import_fiches \
   /tmp/fiches.json --plan <ID_PLAN> --user admin@test.fr
#   → DRY-RUN : affiche ce qui serait créé, rollback, RIEN écrit.
# Ajouter --commit pour persister réellement.
```

## Mapping arborescence → modèles Cicada

| JSON | Modèle Cicada |
|---|---|
| `enjeux[]` | `Enjeu` (`id_categorie` ENJEU/FCR, `rang`=priorité, `categorie_ecologique`, flags `habitat`/`espece`/…) |
| `enjeux[].facteurs[]` | `FacteurInfluence` |
| `…facteurs[].pressions[]` | `Pression` (`id_type_pression` = PressRef, rapproché de `TYPE_PRESSION`) |
| `enjeux[].olts[]` | `ObjectifLongTerme` |
| `…olts[].niveaux_exigence[]` | `NiveauExigence` |
| `…niveaux_exigence[].indicateurs[]` (ÉTAT) | `Indicateur` (`id_ne`, `type_indicateur`=ETAT) |
| `enjeux[].objectifs_operationnels[]` | `ObjectifOperationnel` |
| `…objectifs_operationnels[].resultats_attendus[]` | `ResultatAttendu` |
| `…resultats_attendus[].indicateurs[]` (PRESSION/RÉPONSE) | `Indicateur` (`id_resultat_attendu`) |
| `indicateurs[].metriques[]` | `Metrique` (`nom_metrique`, `description`=valeur cible) |

**#478 — saisie à l'import** : les champs requis absents de la source (types
écologiques de l'enjeu, type PressRef d'une pression) sont **signalés** dans le
rapport (`a_completer` / « pressions sans type ») pour saisie humaine ; l'élément
est créé avec des défauts prudents. Les **métriques** n'importent que le libellé →
l'indicateur reste « indéterminé » (aucune mesure).

Le mapping **actions → `Operation`** est documenté dans le commit du module actions.

## Tests réalisés (sur la base seedée, plan brouillon 1158)

- ✅ Schémas : `arborescence_demo.json` et `extraction_demo.json` valides (`jsonschema`).
- ✅ Import arborescence (dry-run) : 1 enjeu → 1 OLT → 3 NE → 4 indicateurs → 5 métriques ;
  flag `a_completer` (#478) fonctionnel. Relancé 2× sans erreur → **rien persisté**.
- ✅ **End-to-end** : arborescence + actions enchaînées → **6/6 fiches rattachées
  automatiquement** aux indicateurs créés (CS 1.1 → « Surface des pelouses », CS 02
  → « Degré d'humidité », …), le tout en transaction annulée (aucune écriture).

> ⚠️ Leçon : `transaction.savepoint()` est un **no-op hors `atomic()`** (mode
> autocommit) — le dry-run doit envelopper le travail dans `transaction.atomic()`
> et lever une exception pour forcer le rollback. C'est le mécanisme retenu.

## Limites assumées (POC)

- **Pressions/OO** : extraits si présents dans la source ; la table de synthèse
  d'arborescence (tome II) ne décrit souvent que la branche ÉTAT.
- **Titres d'enjeux** : parfois hors de la table de synthèse → à confirmer (signalé).
- **Volume** : un tome III de ~90 opérations dépasse la fenêtre de sortie en un appel ;
  découper par section (`--pages`).
- **Relecture indispensable** sur ~10-20 % des champs (rattachements, budgets renvoyés).

## Industrialisation (au-delà du POC)

- Transformer les imports en actions DRF (`POST /api/plans/plans/{id}/import-arborescence/`
  puis `…/import-fiches/`) avec `CanModifyOnlyDraftPlan`, ou conserver les commandes CLI.
- Découpage automatique des gros tomes + déduplication.
- Écran de relecture/correction in-app (Patron A) une fois la qualité validée.
- Suggestion automatique des types PressRef (rapprochement sémantique pression → CARET).
