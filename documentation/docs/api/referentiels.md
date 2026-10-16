# Référentiels

Référentiels nationaux importés dans chaque instance, en lecture seule. Ils servent à rattacher des espèces, habitats, sites géologiques et protocoles aux éléments d'un plan, et alimentent les listes déroulantes de l'application.

| Référentiel | Préfixe | Endpoints |
|-------------|---------|-----------|
| **TaxRef** (INPN, taxons) | `/api/taxref/` | liste, `{cd_nom}/`, `autocomplete/?q=` (trigrammes, sans accents), `search/{field}/{ilike}/`, `validate-bulk/`, `version/` |
| **HabRef** (INPN, habitats) | `/api/habref/` | liste, `{cd_hab}/`, `autocomplete/?q=` (filtrable par typologie), `typo/`, `correspondance/{cd_hab}/` (classification d'origine et habitats liés), `validate-bulk/` |
| **INPG** (patrimoine géologique) | `/api/inpg/` | liste, `{id_inpg}/`, `autocomplete/?q=`, `validate-bulk/` |
| **Protocoles standardisés** (CAMPanule et MhéO) | `/api/campanule/` | liste, `{cd_protocole}/`, `autocomplete/?q=` |
| **Nomenclatures** (types de sites, statuts, catégories…) | `/api/nomenclatures/` | liste `?type=<mnémonique>`, `{id}/` |

## Usages

- **Autocomplétion** : `GET /api/taxref/autocomplete/?q=limos&limit=20` renvoie les meilleurs candidats par similarité de trigrammes, accents ignorés. Même principe pour les habitats, les sites INPG et les protocoles.
- **Synonymes** : un taxon introuvable sous son nom usuel peut être recherché dans les synonymes ; le nom valide (`cd_ref`) est alors rattaché.
- **Validation en masse** : `POST /api/taxref/validate-bulk/` reçoit une liste de codes `cd_nom`, de noms scientifiques ou vernaculaires et renvoie, pour chacun, le taxon reconnu ou l'anomalie. C'est ce qu'utilise l'import Excel d'une arborescence ; `habref` et `inpg` offrent l'équivalent.
- **Nomenclatures** : chaque type est identifié par son mnémonique (par exemple `TYPE_SITE`, `STATUT_PG`) ; la réponse donne le code, le libellé et la hiérarchie éventuelle.

## Référence interactive

<swagger-ui src="openapi/referentiels.json"/>
