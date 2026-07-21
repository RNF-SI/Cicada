# Référentiels et Nomenclatures

Ce document explique l'intégration et la gestion des données de référence dans Cicada : nomenclatures métier, référentiel taxonomique (TaxRef), référentiel des habitats (HabRef), inventaire géologique (INPG) et catalogue des protocoles (CAMPanule).

> **Inspiré de GeoNature** : L'architecture suit les conventions de GeoNature (noms de schemas, structure des tables, sources de données) pour assurer la compatibilité et faciliter les échanges de données.

---

## Vue d'ensemble des référentiels

| Référentiel | Schema PostgreSQL | Source | Taille | Chargement |
|---|---|---|---|---|
| **Nomenclatures** | `ref_nomenclatures` | Fichiers SQL internes | ~500 entrées | Automatique au démarrage |
| **HabRef** (habitats) | `ref_habitats` | INPN via geonature.fr | ~35 000 habitats | Automatique au démarrage |
| **TaxRef** (taxonomie) | `taxonomie` | INPN via geonature.fr | ~700 000 taxons | Automatique au démarrage |
| **INPG** (géologie) | `ref_inpg` | Projet socle (base INPG de l'INPN) | ~3 956 sites | Automatique au démarrage |
| **CAMPanule** (protocoles) | `ref_campanule` | INPN (PatriNat) | ~4 500 entrées | Automatique au démarrage |

### Provenance des données

- **TaxRef** : Référentiel taxonomique national publié par le MNHN/INPN. Contient l'ensemble des noms scientifiques de la faune, la flore et la fonge de France. Téléchargé depuis `geonature.fr/data/inpn/taxonomie/`. Mis à jour environ 1 fois par an.
- **HabRef** : Référentiel des habitats naturels publié par le MNHN/INPN. Contient les habitats des principales typologies françaises et européennes (EUNIS, Corine Biotope, Natura 2000, etc.). Téléchargé depuis `geonature.fr/data/inpn/habitats/`. Mises à jour très rares.
- **INPG** : Inventaire National du Patrimoine Géologique, géré par le BRGM pour le compte du MNHN. Contient les sites géologiques d'intérêt patrimonial de France. Les données sont extraites du « projet socle » (base INPG de l'INPN), filtrées pour ne conserver que les sites à diffusion publique (`niveau_de_diffusion = 'Public'`). Stockées dans un fichier SQL interne au projet (`backend/inpg_data/inpg_inserts.sql`). **⚠️ L'intégration INPG est susceptible d'évoluer** : le mode de récupération des données pourrait changer à terme (API, téléchargement automatique, etc.).
- **CAMPanule** : CATalogue des Méthodes et des Protocoles de collecte de données naturalistes, publié par PatriNat (OFB/CNRS/MNHN) via l'INPN. Contient les protocoles standardisés, les méthodes et techniques de collecte utilisés en France. Données publiques embarquées dans le projet en CSV (`backend/apps/campanule/data/`). Version 1, septembre 2022.

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

1. `python manage.py migrate` — Crée les schemas et tables (dont `taxonomie`, `ref_habitats` et `ref_inpg`)
2. `python manage.py import_nomenclatures` — Charge les nomenclatures métier
3. `python manage.py import_habref` — Charge le référentiel HabRef (~35k habitats)
4. `python manage.py import_taxref` — Charge le référentiel TaxRef (~700k taxons)
5. `python manage.py import_inpg` — Charge l'INPG (~3 956 sites géologiques)
6. `python manage.py import_campanule` — Charge CAMPanule (~4 500 entrées protocoles/méthodes/techniques)
7. `python create_superuser.py` — Crée le superutilisateur
8. `python manage.py collectstatic` — Fichiers statiques

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
# Import initial (idempotent — skip si déjà fait)
docker compose exec web python manage.py import_nomenclatures

# Upsert : ajouter les nouvelles + mettre à jour les labels/définitions modifiés
docker compose exec web python manage.py import_nomenclatures --force

# Upsert + nettoyage : idem + supprime les entrées absentes des fichiers SQL
docker compose exec web python manage.py import_nomenclatures --force --prune

# Vérification
docker compose exec web python test_nomenclatures.py
```

### Mode upsert intelligent (`--force`)

La commande utilise `INSERT ... ON CONFLICT DO UPDATE` pour :
- **Ajouter** les nouvelles nomenclatures (nouveaux types ou valeurs)
- **Mettre à jour** les labels, définitions ou hiérarchies modifiés
- **Conserver** les données existantes liées par FK (suivis, opérations, etc.)

C'est la méthode recommandée après toute modification des fichiers SQL.

### Nettoyage des obsolètes (`--prune`)

Le flag `--prune` (implique `--force`) supprime en plus les entrées qui ne sont plus présentes dans les fichiers SQL. Si une nomenclature est référencée par des données existantes (FK), elle est conservée avec un avertissement.

**Workflow typique après modification des nomenclatures :**
```bash
# 1. Modifier les fichiers SQL
#    backend/nomenclatures_data/types_inserts.sql
#    backend/nomenclatures_data/nomenclatures_inserts.sql

# 2. Appliquer les changements (ajouter + mettre à jour)
docker compose exec web python manage.py import_nomenclatures --force

# 3. (Optionnel) Supprimer les entrées obsolètes
docker compose exec web python manage.py import_nomenclatures --force --prune
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

## Inventaire géologique (INPG)

### Présentation

L'INPG (Inventaire National du Patrimoine Géologique) recense les sites géologiques d'intérêt patrimonial de France. Il est géré par le BRGM pour le compte du MNHN.

- **Source** : Projet socle (base INPG de l'INPN)
- **Schema** : `ref_inpg`
- **Filtre** : Seuls les sites à diffusion publique sont inclus
- **Données** : Fichier SQL interne (`backend/inpg_data/inpg_inserts.sql`, ~34 Mo)

> **⚠️ Évolution prévue** : Le mode de récupération des données INPG pourrait évoluer à terme (API directe, téléchargement automatique depuis l'INPN, etc.). L'architecture actuelle (fichier SQL embarqué) est une solution temporaire.

### Table

| Table | Description | Taille |
|---|---|---|
| `ref_inpg.inpg` | Sites géologiques (id_inpg = PK) | ~3 956 lignes |

La table contient 88 colonnes dont : `id_inpg`, `id_metier`, `lb_site` (nom), `geom` (MultiPolygon SRID 4326), `region`, `departements`, `communes`, `interet_geol_principal`, `typologie_1/2/3`, notes d'évaluation, dates de validation, etc.

### Commandes

```bash
# Import INPG (automatique au démarrage Docker)
docker compose exec web python manage.py import_inpg

# Forcer le rechargement
docker compose exec web python manage.py import_inpg --force
```

### API REST

| Endpoint | Description |
|---|---|
| `GET /api/inpg/` | Liste paginée des sites INPG |
| `GET /api/inpg/<id_inpg>/` | Détail d'un site |
| `GET /api/inpg/autocomplete/?search=<terme>&limit=20` | Autocomplete trigramme (min 2 caractères) |
| `POST /api/inpg/validate-bulk/` | Validation en masse (id_inpg, id_metier ou nom de site) |

### Utilisation dans le code

```python
from apps.geology.models import Inpg

# Chercher un site par id_inpg
site = Inpg.objects.get(id_inpg=42)

# Recherche par nom
sites = Inpg.objects.filter(lb_site__icontains='grotte')
```

### Mise à jour des données

Pour mettre à jour les données INPG :
1. Exporter la table `inpg` depuis la base du projet socle (DBeaver ou autre outil), en filtrant sur `niveau_de_diffusion = 'Public'`
2. Remplacer le fichier `backend/inpg_data/inpg_inserts.sql`
3. Relancer l'import : `docker compose exec web python manage.py import_inpg --force`

---

## Catalogue des protocoles (CAMPanule)

### Présentation

CAMPanule (CATalogue des Méthodes et des Protocoles) est le référentiel national des protocoles de collecte de données naturalistes, publié par PatriNat (OFB/CNRS/MNHN) via l'INPN.

- **Version actuelle** : v1 (septembre 2022)
- **Mise à jour** : Très rare (v1 depuis 2022, pas de v2 annoncée)
- **Schema** : `ref_campanule`
- **Source** : CSV embarqués dans le projet (`backend/apps/campanule/data/`)
- **Source originale** : https://inpn.mnhn.fr/programme/campanule (format Access .accdb)

> **Note (issue #565) — protocoles standardisés MhéO** : côté interface, on parle désormais de **« protocole standardisé »** plutôt que de « Campanule » (MhéO n'est pas dans CAMPanule, mais a vocation à y être intégré). En plus du catalogue INPN, 5 protocoles standardisés **MhéO** (boîte à outils Milieux humides — Amphibiens, Flore, Odonates, Pédologie, Piézométrie) sont chargés dans les mêmes tables `ref_campanule.*`, dans une **plage de codes réservée** (`cd_protocole >= 900000`, cf. `MHEO_BASE`). Définis en Python dans `backend/apps/campanule/data_mheo.py` (et non en CSV), ils sont ajoutés par `import_campanule` : au premier import complet, et en **top-up idempotent** au démarrage suivant si le catalogue est déjà installé mais que MhéO manque (pas besoin de `--force`).

### Tables

| Table | Description | Taille |
|---|---|---|
| `ref_campanule.protocoles` | Protocoles de collecte (cd_protocole = PK) | ~224 |
| `ref_campanule.methodes` | Méthodes de collecte (cd_methode = PK) | ~15 |
| `ref_campanule.techniques` | Techniques de collecte (cd_technique = PK) | ~178 |
| `ref_campanule.attributs` | Vocabulaire contrôlé (domaine, objectif, cible, matériel) | ~145 |
| `ref_campanule.prot_echantillonnage` | Plans d'échantillonnage par protocole | ~254 |
| `ref_campanule.docs_web` | Références bibliographiques (liens INPN Docs-Web) | ~252 |
| `ref_campanule.prot_attributs_rel` | Relation protocole-attribut (N-N) | ~1 536 |
| `ref_campanule.prot_biblio_rel` | Relation protocole-document (N-N) | ~225 |
| `ref_campanule.prot_meth_rel` | Relation protocole-méthode (N-N) | ~46 |
| `ref_campanule.prot_tech_rel` | Relation protocole-technique (N-N) | ~406 |
| `ref_campanule.meth_attributs_rel` | Relation méthode-attribut (N-N) | ~36 |
| `ref_campanule.meth_biblio_rel` | Relation méthode-document (N-N) | ~30 |
| `ref_campanule.tech_attributs_rel` | Relation technique-attribut (N-N) | ~730 |
| `ref_campanule.tech_biblio_rel` | Relation technique-document (N-N) | ~196 |
| `ref_campanule.autocomplete_protocole` | Table dénormalisée pour l'autocomplete (protocoles non obsolètes) | ~199 |

### Contenu métier

**Catégories de protocoles** (`categorie_prot`) :
- *Protocoles standardisés* : reproductibles, documentés, pour des territoires variés
- *Enquêtes (ponctuelles ou continues)* : science participative, remontées de données
- *Guides et recommandations* : cadres pour la mise en place de suivis

**Groupes cibles** (`cible`) : Oiseaux, Mammifères, Insectes et araignées, Amphibiens et reptiles, Plantes, Habitats, Multi-groupes, etc.

**Catégories d'attributs** :
- `DOMAINE` : Continental terrestre, aquatique, littoral, marin
- `OBJECTIF` : Distribution, dynamique, état de santé, richesse spécifique, etc.
- `TYPE_CIBLE` : Espèce, communauté, habitat
- `MATERIEL` : Piège Malaise, détecteur ultrasons, etc. (techniques uniquement)
- `COLLECTE` : Photographie, spécimen, indice de présence (techniques uniquement)
- `GPE_GRAND_PUBLIC` : Groupes taxonomiques vulgarisés

### Commandes

```bash
# Import CAMPanule (automatique au démarrage Docker)
docker compose exec web python manage.py import_campanule

# Forcer le rechargement
docker compose exec web python manage.py import_campanule --force
```

### Utilisation dans le code

```python
from apps.campanule.models import (
    CampanuleProtocole, CampanuleTechnique, CampanuleProtTechRel,
    AutocompleteProtocole
)

# Chercher un protocole
stoc = CampanuleProtocole.objects.filter(
    lb_protocole_court__icontains='STOC'
).first()

# Techniques utilisées par un protocole
tech_ids = CampanuleProtTechRel.objects.filter(
    cd_protocole=stoc.cd_protocole
).values_list('cd_technique', flat=True)
techniques = CampanuleTechnique.objects.filter(cd_technique__in=tech_ids)

# Recherche autocomplete (protocoles non obsolètes)
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT cd_protocole, lb_protocole_court, cible, categorie_prot
        FROM ref_campanule.autocomplete_protocole
        WHERE search_name ILIKE %s
        ORDER BY similarity(search_name, %s) DESC
        LIMIT 20
    """, ['%oiseaux%', 'oiseaux'])
```

### Mise à jour des données

En cas de nouvelle version de CAMPanule :
1. Télécharger le nouveau `.accdb` depuis https://inpn.mnhn.fr/programme/campanule
2. Exporter les tables en CSV (depuis Access ou via `mdbtools`)
3. Convertir en UTF-8 : `iconv -f CP1252 -t UTF-8 fichier.csv > fichier_utf8.csv`
4. Remplacer les CSV dans `backend/apps/campanule/data/`
5. Si le schéma a changé (nouvelles colonnes/tables), adapter les modèles Django et créer une migration
6. Relancer : `docker compose exec web python manage.py import_campanule --force`

---

## Autocomplete des référentiels

Tous les autocompletes (TaxRef, HabRef, INPG, CAMPanule) fonctionnent sur le même principe :

1. **Minimum 2 caractères** saisis pour déclencher la recherche
2. **Recherche trigramme** (`pg_trgm`) avec `unaccent()` pour l'insensibilité aux accents
3. **Tri par pertinence** via `similarity()` (les résultats les plus proches en premier)
4. **Limite** configurable (défaut : 20 résultats, max : 100)
5. **Cache côté client** pour éviter les requêtes redondantes

| Référentiel | Champs recherchés | Endpoint |
|---|---|---|
| TaxRef | Nom scientifique + nom vernaculaire (via vue matérialisée) | `/api/taxref/autocomplete/` |
| HabRef | Nom français + code nomenclature (via table dénormalisée) | `/api/habref/autocomplete/` |
| INPG | Nom du site (`lb_site`) + code métier (`id_metier`) | `/api/inpg/autocomplete/` |
| CAMPanule | Libellé court + complet + auteur + cible (via table dénormalisée) | *(API à venir)* |

### Import en masse

Chaque référentiel dispose aussi d'un endpoint `validate-bulk` (POST) qui permet de valider une liste d'entrées (codes ou noms) en une seule requête. L'auto-détection du format (numérique = code, texte = nom) permet de mélanger les formats. Les entrées non trouvées sont accompagnées de suggestions (candidats les plus proches par trigramme).

---

## Architecture technique

### Schemas PostgreSQL

Cicada utilise 12 schemas PostgreSQL :

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
| `ref_inpg` | Cicada | Inventaire géologique INPG |
| `ref_campanule` | Cicada/INPN | Catalogue des protocoles CAMPanule |

### Extensions PostgreSQL requises

| Extension | Usage |
|---|---|
| `postgis` | Données géospatiales |
| `pg_trgm` | Index trigramme pour l'autocomplete (TaxRef, HabRef, INPG, CAMPanule) |
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

### Nomenclatures manquantes ou labels incorrects
```bash
# Met à jour les labels/définitions et ajoute les nouvelles entrées
docker compose exec web python manage.py import_nomenclatures --force
docker compose exec web python test_nomenclatures.py
```

### Nomenclatures obsolètes à supprimer
```bash
# Supprime les entrées qui ne sont plus dans les fichiers SQL
# (les entrées référencées par des données existantes sont conservées)
docker compose exec web python manage.py import_nomenclatures --force --prune
```
