# POC — Import IA de plans de gestion existants

Proof of concept pour l'intégration de **plans de gestion textuels existants** (PDF
hétérogènes) dans Cicada, en extrayant automatiquement les **fiches actions** vers
l'arborescence Cicada. **Branche `poc/import-plans-ia` — rien n'est câblé dans
l'application qui tourne.**

> Décision de périmètre : on importe les **fiches actions / opérations**, pas les
> métriques chiffrées (trop complexes). L'arborescence (enjeux → OLT → NE →
> indicateurs) est supposée **déjà saisie dans Cicada** ; l'import s'y rattache.

## La chaîne (3 étapes découplées)

```
 PDF (tome III, hétérogène)
        │  (1) extraction LLM multimodale
        ▼
   JSON normalisé  ──(2)──►  Excel modèle Cicada   (relecture humaine)
        │                         (fiches_remplies.xlsx)
        │  (3) import
        ▼
   Operations (brouillon) rattachées aux indicateurs du plan
```

Le **format intermédiaire JSON** (validé contre `cicada_fiche_action_schema.json`)
est le pivot : il permet la relecture/correction humaine avant toute écriture en base.
L'objectif n'est pas l'automatisation totale mais de passer de **~3 jours à ~½ journée**
par plan, l'IA produisant un brouillon à 80-90 % qu'un gestionnaire corrige.

## Fichiers

| Fichier | Rôle |
|---|---|
| `cicada_fiche_action_schema.json` | Schéma cible (aligné sur l'export Cicada "Fiche action"). |
| `extract_fiches.py` | (1) PDF → JSON via l'API Claude (sortie structurée, anti-hallucination). |
| `json_to_excel.py` | (2) JSON → classeur Excel au format du modèle Cicada (1 onglet/fiche). |
| `poc_import_fiches.py` | (3) JSON → `Operation` brouillon en base (commande Django isolée). |
| `templates/modele_export_fiche_action.xlsx` | Le modèle d'export Cicada de référence. |
| `sample_output/extraction_demo.json` | 6 fiches réelles extraites (Val Suzon + Mépieu), validées. |
| `sample_output/fiches_remplies.xlsx` | Sortie (2) générée à partir de la démo. |

## Utilisation

### (1) Extraction PDF → JSON  *(nécessite une clé API Anthropic — distincte de l'abonnement Max)*
```bash
pip install "anthropic>=0.92" jsonschema pypdf
export ANTHROPIC_API_KEY=sk-ant-...
python extract_fiches.py "tome_iii.pdf" --pages 17-40 --out fiches.json
```
Coût indicatif : ~0,5 à 3 € par plan. Sans clé, on peut produire le JSON via
Claude Code directement (voir la démo `sample_output/extraction_demo.json`).

### (2) JSON → Excel  *(relecture humaine)*
```bash
pip install openpyxl
python json_to_excel.py sample_output/extraction_demo.json -o sample_output/fiches_remplies.xlsx
```

### (3) Import en base  *(commande Django — dry-run par défaut)*
```bash
# Copier la commande dans l'arbre de l'app SEULEMENT pour tester :
cp poc/import-ia/poc_import_fiches.py \
   backend/apps/plans/management/commands/poc_import_fiches.py

docker compose exec web python manage.py poc_import_fiches \
   /chemin/extraction.json --plan <ID_PLAN> --user admin@test.fr
#   → DRY-RUN : affiche ce qui serait créé, rollback, rien écrit.
# Ajouter --commit pour persister réellement.
```

## Mapping schéma → modèle Cicada (`Operation`)

| Champ JSON | Champ `Operation` |
|---|---|
| `intitule` | `libelle` |
| `code_action` | `code_operation` |
| `priorite` | `id_priorite` (nomenclature `PRIORITE_OPERATION`) |
| `code_nature` / `code_action` | `id_type_action` (nomenclature `TYPE_ACTION`, best-effort) |
| `operation.details` (+ protocole) | `description` |
| `operation.operateurs_*` | `operateurs` |
| `operation.partenaires` | `partenaires` |
| `programmation.financements[].organisme_ou_financeur` | `financeurs` |
| `programmation.calendrier_annuel` | `annee_min`/`annee_max`, `programmation_annuelle`, lignes `OperationAnnee` |
| `cadre.indicateur` | **rattachement** → `id_indicateur` (match sur `Indicateur.nom_indicateur` du plan) |
| `cadre.enjeu/olt/niveau_exigence` | servent au rattachement / relecture (non écrits : déjà dans l'arborescence) |
| `metriques` | non importées (hors périmètre) |

## Limites assumées (POC)

- **Rattachement** : si `cadre.indicateur` ne correspond à aucun indicateur du plan,
  l'opération est créée **non rattachée** et signalée — rattachement manuel par le
  gestionnaire. C'est volontaire : l'IA ne crée pas d'arborescence.
- **Volume** : un tome III de ~90 opérations dépasse la fenêtre de sortie en un appel ;
  utiliser `--pages` pour découper par section (production : boucle de chunking).
- **Relecture indispensable** : ~10-20 % des champs (budgets renvoyés ailleurs,
  rattachements) à vérifier. `extraction_meta.champs_incertains` priorise la relecture.
- **Statut** : les opérations sont créées en `draft` (jamais validées automatiquement).

## Industrialisation (au-delà du POC)

- Transformer (3) en action DRF (`POST /api/plans/plans/{id}/import-fiches/`) avec
  `CanModifyOnlyDraftPlan`, ou conserver la commande CLI pour un import supervisé.
- Découpage automatique des gros tomes + déduplication par `code_action`.
- Écran de relecture/correction in-app (Patron A) une fois la qualité validée.
