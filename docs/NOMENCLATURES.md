# Référentiels et Nomenclatures

Ce document explique l'intégration et la gestion des données de référence dans Cicada : nomenclatures métier, référentiel taxonomique (TaxRef) et référentiel des habitats (HabRef).

> **Inspiré de GeoNature** : L'architecture suit les conventions de GeoNature (noms de schemas, structure des tables, sources de données) pour assurer la compatibilité et faciliter les échanges de données.

---

## Vue d'ensemble des référentiels

| Référentiel | Schema PostgreSQL | Source | Taille | Chargement |
|---|---|---|---|---|
| **Nomenclatures** | `ref_nomenclatures` | Fichiers SQL internes | ~500 entrées | Automatique au démarrage |
| **HabRef** (habitats) | `ref_habitats` | INPN via geonature.fr | ~35 000 habitats | Automatique au démarrage |
| **TaxRef** (taxonomie) | `taxonomie` | INPN via geonature.fr | ~700 000 taxons | Automatique au démarrage |

### Mode lite pour les tests

TaxRef propose un mode `--lite` qui ne charge que ~8 000 taxons représentatifs au lieu de ~700 000. C'est utile pour :
- Le **développement local** (démarrage plus rapide)
- Les **tests CI** (pas besoin de l'intégralité du référentiel)
- Les **environnements de démonstration**

Pour activer le mode lite, ajouter dans votre `.env` :
```bash
TAXREF_IMPORT_OPTS=--lite
```

Le mode lite ne garde que :
- Les noms de référence (cd_nom = cd_ref, pas les synonymes)
- Les rangs espèce et supérieurs (pas les sous-espèces, variétés)
- Un cap par groupe taxonomique (~700 oiseaux, ~250 mammifères, ~3000 angiospermes, etc.)

---

## Installation

### Première installation (Docker)

```bash
# 1. Lancer les services — tout est chargé automatiquement
docker compose up -d

# 2. (Optionnel) Créer les données de test
docker compose exec web python manage.py seed_testdata
```

**Ce qui se passe automatiquement au démarrage :**

1. `python manage.py migrate` — Crée les schemas et tables (dont `taxonomie` et `ref_habitats`)
2. `python manage.py import_nomenclatures` — Charge les nomenclatures métier
3. `python manage.py import_habref` — Charge le référentiel HabRef (~35k habitats)
4. `python manage.py import_taxref` — Charge le référentiel TaxRef (~700k taxons)
5. `python create_superuser.py` — Crée le superutilisateur
6. `python manage.py collectstatic` — Fichiers statiques

**Pour accélérer le démarrage en développement**, ajouter dans `.env` :
```bash
TAXREF_IMPORT_OPTS=--lite
```
Cela charge uniquement ~8 000 taxons représentatifs au lieu de ~700 000.

### Comparaison avec GeoNature

| Étape | GeoNature | Cicada |
|---|---|---|
| Schemas BD | Alembic branches | Django migrations |
| Nomenclatures | Auto (Alembic `nomenclatures_inpn_data`) | Auto (`import_nomenclatures`) |
| HabRef | Auto (Alembic `habitats_inpn_data`) | Auto (`import_habref`) |
| TaxRef | Manuel (`geonature taxref import-v18`) | Manuel (`import_taxref`) |
| Réf. géographiques | Optionnel (flags dans `install_all.ini`) | Non implémenté |

---

## Nomenclatures métier

### Structure des données

**Types de nomenclatures** (`ref_nomenclatures.bib_nomenclatures_types`) :
- **id_type** : Identifiant unique
- **mnemonique** : Code mnémonique du type
- **label** : Libellé descriptif
- **definition** : Définition détaillée

**Nomenclatures** (`ref_nomenclatures.t_nomenclatures`) :
- **id_nomenclature** : Identifiant unique
- **id_type** : Référence vers le type
- **cd_nomenclature** : Code technique unique (ex: `RNN`, `RNR`)
- **mnemonique** : Mnémonique métier
- **label** : Libellé affiché
- **hierarchy** : Code hiérarchique (optionnel)
- **actif** : Indicateur d'activation

### Commandes

```bash
# Import (idempotent — skip si déjà fait)
docker compose exec web python manage.py import_nomenclatures

# Forcer la réimportation
docker compose exec web python manage.py import_nomenclatures --force

# Vérification
docker compose exec web python test_nomenclatures.py
```

### Utilisation dans le code

```python
from apps.core.models import TypeNomenclature, Nomenclature

# Par type
type_espace = TypeNomenclature.objects.get(mnemonique='Espace naturel')
espaces = Nomenclature.objects.filter(id_type=type_espace)

# Par mnémonique
rnn = Nomenclature.objects.get(mnemonique='RNN')
```

### API REST

- `GET /api/nomenclatures/types/` — Liste des types
- `GET /api/nomenclatures/` — Liste des nomenclatures (filtrage et recherche)

### Fichiers de données

- `backend/nomenclatures_data/types_inserts.sql` — Types de nomenclatures
- `backend/nomenclatures_data/nomenclatures_inserts.sql` — Nomenclatures

---

## Référentiel taxonomique (TaxRef)

### Présentation

TaxRef est le référentiel taxonomique national de l'INPN. Il contient l'ensemble des espèces de la faune, la flore et la fonge de France (~700 000 noms).

- **Version actuelle** : v18 (2025)
- **Mise à jour** : ~1 fois/an par l'INPN
- **Schema** : `taxonomie`
- **Source** : `geonature.fr/data/inpn/taxonomie/TAXREF_v18_2025.zip`

### Tables

| Table | Description | Taille |
|---|---|---|
| `taxonomie.taxref` | Table principale (cd_nom = PK) | ~700k lignes |
| `taxonomie.bib_taxref_rangs` | Rangs taxonomiques (Règne, Classe, Espèce...) | ~16 entrées |
| `taxonomie.bib_taxref_habitats` | Types d'habitats associés (Marin, Terrestre...) | 8 entrées |
| `taxonomie.bib_taxref_statuts` | Statuts taxonomiques (Présent, Endémique...) | ~15 entrées |
| `taxonomie.t_meta_taxref` | Versioning du référentiel | 1 entrée |
| `taxonomie.vm_taxref_list_forautocomplete` | **Vue matérialisée** pour l'autocomplete | ~350k lignes |

### Commandes

```bash
# Import complet TaxRef v18 (version par défaut — ~700k taxons)
docker compose exec web python manage.py import_taxref

# Import allégé (~8000 taxons — pour dev/tests)
docker compose exec web python manage.py import_taxref --lite

# Version spécifique
docker compose exec web python manage.py import_taxref --version 17

# Forcer le rechargement
docker compose exec web python manage.py import_taxref --force

# Passer de lite à complet
docker compose exec web python manage.py import_taxref --force

# Spécifier le répertoire de cache (défaut: /tmp/cicada_taxref_cache/)
docker compose exec web python manage.py import_taxref --cache-dir /data/cache

# Rafraîchir la vue matérialisée (après modification des données)
docker compose exec web python manage.py refresh_taxref_views
```

### Processus d'import détaillé

1. **Téléchargement** du ZIP (~100 Mo) avec cache local
2. **Décompression** dans le répertoire de cache
3. **Chargement des données de référence** (rangs, habitats, statuts)
4. **Chargement du CSV principal** via `COPY FROM STDIN` (encodage WIN1252, délimiteur tabulation)
5. **Création de la vue matérialisée** `vm_taxref_list_forautocomplete` (noms valides uniquement, concaténation nom latin + nom vernaculaire)
6. **Indexation trigramme** (`gin_trgm_ops`) + `unaccent()` pour la recherche floue
7. **Mise à jour des métadonnées** (version, date)

### Cache local

Les fichiers téléchargés sont conservés dans `/tmp/cicada_taxref_cache/` :
- Le ZIP n'est pas re-téléchargé s'il existe déjà
- Le répertoire décompressé est réutilisé
- Pour forcer un nouveau téléchargement, supprimer le cache ou utiliser un autre répertoire

### API REST

| Endpoint | Description |
|---|---|
| `GET /api/taxref/version/` | Version courante du référentiel |
| `GET /api/taxref/` | Liste paginée avec filtres (`regne`, `group2_inpn`, `id_rang`, `valid_only`) |
| `GET /api/taxref/<cd_nom>/` | Détail d'un taxon |
| `GET /api/taxref/autocomplete/?search=<terme>&limit=20` | Autocomplete trigramme (min 2 caractères) |
| `GET /api/taxref/search/<field>/<ilike>/` | Recherche libre sur un champ |

### Utilisation dans le code

```python
from apps.taxonomy.models import Taxref, TMetaTaxref

# Chercher un taxon par cd_nom
loup = Taxref.objects.get(cd_nom=60577)

# Taxons valides d'un groupe
oiseaux = Taxref.objects.filter(
    group2_inpn='Oiseaux',
    cd_nom=F('cd_ref')  # Noms valides uniquement
)

# Version installée
meta = TMetaTaxref.objects.filter(referential_name='taxref').first()
```

### Bonnes pratiques

- **Pas de FK vers TaxRef** depuis vos tables métier — stocker `cd_nom` comme entier et valider à l'import. Cela permet de mettre à jour TaxRef sans casser les relations.
- **Rafraîchir la vue matérialisée** après toute modification manuelle des données.
- **Prévoir les mises à jour annuelles** : TaxRef est mis à jour ~1 fois/an. La commande `import_taxref --force` permet de recharger.

---

## Référentiel des habitats (HabRef)

### Présentation

HabRef est le référentiel des habitats naturels de l'INPN. Il contient les habitats des principales typologies françaises et européennes.

- **Version actuelle** : 5.0
- **Mise à jour** : Très rare
- **Schema** : `ref_habitats`
- **Source** : `geonature.fr/data/inpn/habitats/HABREF_50.zip`

### Tables

| Table | Description |
|---|---|
| `ref_habitats.typoref` | Typologies d'habitats (EUNIS, Corine Biotope, Natura 2000...) |
| `ref_habitats.habref` | Table principale des habitats (cd_hab = PK) |
| `ref_habitats.habref_corresp_hab` | Correspondances entre typologies |
| `ref_habitats.habref_corresp_taxon` | Correspondances habitat-taxon |
| `ref_habitats.autocomplete_habitat` | Table dénormalisée pour l'autocomplete |

### Commandes

```bash
# Import HabRef (automatique au démarrage Docker)
docker compose exec web python manage.py import_habref

# Forcer le rechargement
docker compose exec web python manage.py import_habref --force

# Spécifier le répertoire de cache
docker compose exec web python manage.py import_habref --cache-dir /data/cache
```

### API REST

| Endpoint | Description |
|---|---|
| `GET /api/habref/<cd_hab>/` | Détail d'un habitat |
| `GET /api/habref/autocomplete/?search=<terme>&cd_typo=<id>&limit=20` | Autocomplete trigramme |
| `GET /api/habref/typo/` | Liste des typologies |
| `GET /api/habref/correspondance/<cd_hab>/` | Correspondances entre typologies |

### Utilisation dans le code

```python
from apps.habitats.models import Habref, Typoref

# Chercher un habitat
habitat = Habref.objects.get(cd_hab=1234)

# Habitats d'une typologie
eunis = Habref.objects.filter(cd_typo=7)  # EUNIS
```

---

## Architecture technique

### Schemas PostgreSQL

Cicada utilise 10 schemas PostgreSQL :

| Schema | Source | Description |
|---|---|---|
| `utilisateurs` | GeoNature | Utilisateurs et organismes |
| `referentiels` | ODASE | Espaces protégés |
| `ref_nomenclatures` | GeoNature | Nomenclatures métier |
| `ref_geo` | GeoNature | Référentiels géographiques (futur) |
| `general` | ODASE | Plans de gestion |
| `fichiers` | ODASE | Fichiers attachés |
| `ccd_commons` | Cicada | Modules et logs |
| `ccd_notifications` | Cicada | Notifications et validations |
| `taxonomie` | GeoNature | Référentiel taxonomique TaxRef |
| `ref_habitats` | GeoNature | Référentiel des habitats HabRef |

### Extensions PostgreSQL requises

| Extension | Usage |
|---|---|
| `postgis` | Données géospatiales |
| `pg_trgm` | Index trigramme pour l'autocomplete (TaxRef, HabRef) |
| `unaccent` | Recherche insensible aux accents |
| `uuid-ossp` | Génération d'UUID |

### Performance de l'autocomplete

L'autocomplete sur 700k taxons fonctionne en <50ms grâce à :
1. **Vue matérialisée** : pré-calcule `search_name` = nom latin + nom vernaculaire
2. **Index trigramme** (`gin_trgm_ops`) : recherche partielle performante
3. **`unaccent()`** : insensibilité aux accents sans pénalité de performance
4. **`similarity()`** : tri par pertinence (les résultats les plus proches en premier)

---

## Administration Django

### Accès
- **URL** : http://localhost:8000/admin/
- **Sections** : Core > Nomenclatures, Taxonomy > Taxons, Habitats > Habitats

### Fonctionnalités
- Consultation des nomenclatures, taxons et habitats
- Recherche par mnémonique, label ou définition
- Filtrage par type, statut, source, règne, groupe INPN

---

## Troubleshooting

### TaxRef : import échoue au téléchargement
```bash
# Vérifier la connectivité réseau
docker compose exec web wget -q --spider https://geonature.fr/data/inpn/taxonomie/TAXREF_v18_2025.zip

# Télécharger manuellement et placer dans le cache
docker compose exec web mkdir -p /tmp/cicada_taxref_cache
# Copier le ZIP dans le container puis :
docker compose exec web python manage.py import_taxref --cache-dir /tmp/cicada_taxref_cache
```

### HabRef : tables vides après import
```bash
# Vérifier que l'import a bien tourné
docker compose logs web | grep -i habref

# Forcer le rechargement
docker compose exec web python manage.py import_habref --force
```

### Autocomplete lent (>200ms)
```bash
# Vérifier que les index trigramme existent
docker compose exec db psql -U cicada_user -d cicada -c "\di taxonomie.*trgm*"

# Rafraîchir la vue matérialisée
docker compose exec web python manage.py refresh_taxref_views
```

### Nomenclatures manquantes
```bash
docker compose exec web python manage.py import_nomenclatures --force
docker compose exec web python test_nomenclatures.py
```
