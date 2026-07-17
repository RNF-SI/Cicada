# Import IA d'un plan de gestion existant → Cicada

Outil **hors-application** qui lit un plan de gestion **PDF** (hétérogène) et
produit le JSON attendu par les endpoints d'import « sans fichier » de Cicada.
L'IA fournit un brouillon à 80-90 % ; un gestionnaire **relit et corrige** dans
la grille (#9) avant l'import réel. Objectif : passer de ~3 jours à ~½ journée
par plan repris.

Ce dossier **remplace** l'ancien POC `poc/import-ia` (branche `poc/import-plans-ia`,
jamais mergée) : on garde sa moitié « extraction PDF → JSON via Claude » et on
**cible directement la couture JSON** du pipeline d'import V1 (au lieu d'un
schéma + import CLI maison, désormais assurés par le backend).

```
PDF (tome II arborescence / tome III fiches actions)
  │  extract.py  (API Claude, lecture PDF multimodale)
  ▼
payload.json  { "data": { <onglet>: [ {colonne: valeur} ] }, "meta": {...} }
  │  POST /api/plans/plans/{id}/import-{cible}/validate-data   (dry-run → rapport)
  ▼
relecture / correction dans la grille #9 (in-app)
  │  POST /api/plans/plans/{id}/import-{cible}/import-data      (création)
  ▼
brouillon de plan rempli, éditable dans Cicada
```

## Deux cibles, une seule logique

Le format de sortie est **piloté par le schéma** renvoyé par Cicada, donc
`extract.py` couvre les deux modules de l'import (#478) :

| Cible | Onglets produits | Schéma |
|---|---|---|
| `arborescence` | enjeux, facteurs, pressions, olt, ne, oo, ra, indicateurs, metriques (+ taxons, habitats) | **statique** → `schema_arborescence.json` (fourni) |
| `actions` | actions, budgets, rh | **spécifique au plan** → `GET …/import-actions-schema/` |

> Le schéma des **actions dépend du plan** : il embarque la liste de ses
> indicateurs (et postes) avec leur **code de rattachement**, que l'IA réutilise
> pour relier chaque action à son indicateur. On **importe donc l'arborescence
> d'abord**, puis les actions.

## Prérequis

```bash
pip install "anthropic>=0.92"   # + "pypdf" si vous utilisez --pages
export ANTHROPIC_API_KEY=sk-ant-...   # console.anthropic.com — DISTINCT de l'abo Claude Max
```

Coût indicatif : **~0,5 à 3 € par plan** (lecture PDF multimodale incluse).

## Utilisation

### 1. Arborescence (schéma statique fourni)

```bash
python extract.py --target arborescence \
    --pdf tome_ii.pdf --pages 30-60 \
    --out arbo.json
```

### 2. Actions (schéma du plan à récupérer d'abord)

Le schéma embarque les indicateurs de rattachement → on le télécharge depuis le
plan cible (JWT d'un gestionnaire du plan) :

```bash
python extract.py --target actions \
    --pdf tome_iii.pdf --pages 17-90 \
    --schema-url https://cicada.example.fr/api/plans/plans/1444/import-actions-schema/ \
    --token "$JWT" \
    --out actions.json
```

### 3. (option) Valider le JSON produit contre le plan (dry-run)

```bash
python extract.py --target actions ... \
    --plan-url https://cicada.example.fr/api/plans/plans/1444/ --token "$JWT"
# → imprime le rapport : importable ? nombre d'erreurs/avertissements + détail.
```

Puis, dans Cicada, ouvrir la page **Paramètres du plan → Import** et coller /
importer le JSON via la grille de correction (#9), ou poster directement sur
`…/import-{cible}/import-data/`.

### Debug du format (sans clé API)

```bash
python extract.py --target arborescence --pdf x --dry-run-prompt   # imprime le prompt
python3 selftest.py                                                # teste les fonctions pures
```

## Notes

- **Anti-hallucination** : le prompt interdit d'inventer une valeur (absente →
  vide), impose de recopier les intitulés, et fait remonter les champs
  incertains dans `meta.champs_incertains` (à relire en priorité).
- **Liens par code** : l'IA invente des codes courts (E1, F1, I1, A1…) et les
  réutilise pour relier les lignes entre onglets (comme le modèle Excel). Un lien
  cassé est signalé par `validate-data` et se corrige dans la grille.
- **Verrou brouillon (#248)** : `import-data` (et `validate-data`) ne
  fonctionnent que sur un plan en statut `draft`.
- **Périmètre non couvert** (comme la V1 Excel) : grille de scoring des métriques,
  suivis/inventaires CAMPanule, budget par organisme, responsabilités
  site/organisme. Voir `docs/IMPORT_PLANS_GUIDE.md`.
- **Régénérer `schema_arborescence.json`** après une évolution du format :
  ```bash
  docker compose exec -T web python -c "import django,os,json;\
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.development');django.setup();\
from apps.plans.services_import import describe_schema,_load_nomenclature_values,TYPES_ECOLOGIQUES,TYPES_SOCIOECO;\
nom=_load_nomenclature_values();voc={'ecolo':list(TYPES_ECOLOGIQUES),'socio':list(TYPES_SOCIOECO)};\
sh=describe_schema();[c.__setitem__('values',nom.get(c['nomenclature'],[]) if c.get('nomenclature') else voc.get(c['vocab'],[])) for s in sh for c in s['columns'] if c.get('nomenclature') or c.get('vocab')];\
print(json.dumps({'sheets':sh},ensure_ascii=False,indent=2))" > tools/import-ia/schema_arborescence.json
  ```
