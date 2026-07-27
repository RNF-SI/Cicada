# Index de recherche — exploration des données

Ce document décrit le moteur de recherche qui alimente la page **Exploration des
données** (`/exploration`) : rechercher un plan de gestion, ou rechercher dans le
**contenu** des plans de gestion (enjeux, facteurs, pressions, objectifs,
indicateurs, actions).

---

## Pourquoi PostgreSQL et pas Elasticsearch

La recherche s'appuie sur PostgreSQL (`tsvector` + `pg_trgm` + `unaccent`), avec
un index dénormalisé dédié. Ce choix est délibéré :

- **Volume** : une fois les ~4 400 plans repris, l'index contiendra de l'ordre de
  1,3 M de documents faits de libellés courts. Un index GIN répond en quelques
  dizaines de millisecondes sur ce volume.
- **Cohérence avec l'existant** : CICADA exploite déjà plus lourd en Postgres —
  TaxRef fait ~700 000 lignes avec index trigramme et sert l'autocomplete en
  production. Le motif « table dénormalisée + index GIN » est déjà l'idiome du
  projet (`vm_taxref_list_forautocomplete`, `autocomplete_habitat`,
  `autocomplete_protocole`).
- **Coût d'exploitation** : CICADA est installé chez des clients via un paquet
  Debian. Elasticsearch ajouterait un service JVM (~2 Go de RAM) à packager,
  sauvegarder et migrer sur chaque installation, plus un index susceptible de
  diverger silencieusement de la base.

Le **pipeline d'indexation** (extraction des documents → écriture dans l'index)
est volontairement séparé du **stockage** de l'index, pour qu'une bascule
ultérieure reste locale. Seuil de bascule retenu : une recherche dépassant
~300 ms au p95 sur volume réel. Un éventuel besoin de recherche sémantique
passerait par `pgvector` dans le même PostgreSQL, pas par Elasticsearch.

---

## Périmètre indexé

| | |
|---|---|
| **Plans** | Seulement `valide`, `modifie`, `archive` (`PlanGestion.VALIDATED_STATUSES`). Un brouillon n'est jamais explorable, un plan en workflow CSRPN non plus. |
| **Types de contenu** | enjeu, facteur d'influence, pression, objectif à long terme, objectif opérationnel, indicateur, action (`Operation`). |
| **Non indexé** | métriques, mesures, réalisations, résultats attendus, niveaux d'exigence, protocoles, suivis/inventaires — ces objets ne sont visibles que dans l'arborescence du plan. |

---

## Structure de l'index

Table unique `ccd_search.t_recherche_contenu`, une ligne par objet explorable.

**Un seul index pour tous les types** : l'onglet « Tout » et le tri par
pertinence transverse imposent de classer pressions, actions et enjeux dans une
même liste, ce que des index séparés aux scores non comparables ne permettent
pas.

### Colonnes

| Groupe | Colonnes | Rôle |
|---|---|---|
| Identité | `type_contenu`, `id_objet`, `id_pg` | Retrouver l'objet métier |
| Texte | `titre`, `description`, `contexte` | Ce qui est recherché |
| Affichage | `parent_type`, `parent_libelle`, `sous_type`, `sous_type_libelle` | Tuile de résultat |
| Facettes | `statut_pg`, `annee_debut`, `annee_fin`, `site_ids`, `organisme_ids`, `type_site_codes`, `area_ids` | Filtres + compteurs |
| Vecteurs | `search_titre`, `search_full` | Colonnes **générées** par PostgreSQL |

Seules les données nécessaires au **filtrage et aux compteurs** sont
dénormalisées. Les libellés d'affichage (nom du plan, du site, du gestionnaire
principal) sont joints à la volée : une page ne montre que 10 à 20 résultats, et
une donnée jointe ne peut pas devenir obsolète.

### Les deux vecteurs de recherche

Ce sont des **colonnes générées** : elles ne peuvent pas diverger du texte
indexé, et aucune étape Python ne peut être oubliée.

- `search_titre` — les seuls libellés. Alimente le mode « rechercher dans les
  titres uniquement », **activé par défaut** dans l'interface.
- `search_full` — libellé (poids A) + description (poids B) + contexte (poids C).
  Mode élargi.

La configuration plein texte est `public.french_unaccent` : le dictionnaire
`french` radicalise (`limicoles` → `limicol`) mais ne retire pas les accents, si
bien que « foret » ne trouverait pas « forêt ». On chaîne donc `unaccent` avant
`french_stem`.

### Le « contexte » et la recherche élargie

La colonne `contexte` porte, pour chaque objet, **le libellé de l'enjeu dont il
descend et les taxons / habitats / éléments géologiques rattachés à cet enjeu**,
en plus des libellés de ses ancêtres directs.

C'est ce qui rend possible la recherche décrite dans l'aide de la maquette :

> les indicateurs pour lesquels il y a un **enjeu** autour des « limicoles »
> (pour cela, vous devez inclure les résultats plus élargis…)

Un indicateur nommé « Nombre de couples nicheurs » ressort donc sur la requête
`limicole` en mode élargi, et sur `Calidris alpina` — le nom scientifique du
taxon rattaché à son enjeu — alors qu'aucun de ces mots n'apparaît dans son
libellé.

---

## Quand l'index est-il mis à jour

L'index suit le **cycle de vie du plan**, pas ses écritures de contenu : c'est
possible parce qu'un plan n'est indexable qu'une fois validé, et que le contenu
d'un plan validé est verrouillé en lecture seule (#248).

| Évènement | Effet |
|---|---|
| Plan `draft → valide` / `modifie` / `archive` | Indexation complète du plan |
| Plan → `draft` (ou workflow CSRPN) | Désindexation complète |
| Plan supprimé | Lignes supprimées en CASCADE |
| Site ajouté / retiré du plan | Mise à jour des seules facettes |
| Période du plan modifiée | Mise à jour des seules facettes |

Les signaux vivent dans `apps/search/signals.py`. Une erreur d'indexation est
journalisée **sans être propagée** : une recherche temporairement incomplète est
un moindre mal comparé à une validation de plan qui échoue.

---

## API

```
GET /api/exploration/contenus/       # rechercher dans le contenu des plans
GET /api/exploration/plans/          # rechercher un plan de gestion
GET /api/exploration/plans/<slug>/   # fiche publique d'un plan, en lecture seule
GET /api/geo/zones/                  # arbre régions → départements (filtre)
```

**Périmètre volontairement transverse.** Ces deux vues n'appliquent **pas** le
périmètre de lecture de `apps/plans/access.py` (#610) : l'exploration est un
outil de partage inter-organismes, tout utilisateur connecté voit les plans de
tous les organismes. Ce qui la borne, c'est l'index lui-même — seuls les plans
validés, modifiés ou archivés y figurent — et les champs exposés, qui ne
contiennent ni budget, ni RH, ni données empiriques.

### Paramètres

| Paramètre | Contenus | Plans | Effet |
|---|:-:|:-:|---|
| `q` | ✓ | ✓ | Mot-clé. Côté plans : nom du plan, du site, du département ou de la région |
| `titres_seulement` | ✓ | | `true` (défaut) = `search_titre`, `false` = `search_full` |
| `types` | ✓ | | Types de données (dropdown de la barre de recherche) |
| `onglet` | ✓ | | Onglet actif — filtre la liste **sans** toucher aux compteurs. Accepte plusieurs types : la maquette n'affiche qu'un onglet « Objectifs », qui vaut `onglet=objectif_lt,objectif_op` |
| `zones` | ✓ | ✓ | IDs `ref_geo` (départements et/ou régions, indifféremment) |
| `organismes` | ✓ | ✓ | IDs d'organismes gestionnaires |
| `types_site` | ✓ | ✓ | Mnémoniques (`RNN`, `RNR`, `PNR`, `ENS`…) |
| `categories_enjeu` | ✓ | | `ecologique` / `socioeco` |
| `types_indicateur` | ✓ | | `ETAT` / `PRESSION` / `REPONSE` |
| `categories_action` | ✓ | | `SP`, `CS`, `EI`, `IP`… |
| `statuts` | ✓ | ✓ | `en_cours` / `valide` / `archive` |
| `tri` | ✓ | ✓ | `pertinence` (défaut) / `alphabetique` / `recent` |
| `page`, `page_size` | ✓ | ✓ | Pagination (20 par défaut, 100 max) |

Les paramètres multi-valeurs acceptent la forme `?types=enjeu,pression` comme
la forme répétée `?types=enjeu&types=pression`.

### Deux conventions à connaître

**Les compteurs ignorent l'onglet actif.** Ils sont calculés avant `onglet`,
sinon sélectionner « Pressions » ferait tomber tous les autres onglets à zéro
et l'utilisateur ne pourrait plus revenir en arrière.

```json
{
  "pagination": { "count": 2, "current_page": 1, "...": "..." },
  "compteurs": { "tout": 24, "enjeu": 8, "pression": 2, "action": 16, "...": 0 },
  "results": [ ... ]
}
```

**Chaque groupe de facettes ne raffine que son propre type.** Cocher
« Indicateur d'état » restreint les indicateurs mais laisse passer les enjeux,
pressions et actions : les onglets restent utilisables. *Hypothèse de lecture
de la maquette, à confirmer avec la maîtrise d'ouvrage* — l'autre lecture
possible serait que cocher une facette restreigne la recherche au type
correspondant.

### La fiche publique

`GET /api/exploration/plans/<slug>/` renvoie la **structure** d'un plan validé :
enjeux, facteurs d'influence, pressions, objectifs à long terme et
opérationnels, niveaux d'exigence, résultats attendus, indicateurs, métriques et
actions programmées.

C'est le seul endroit du projet où le contenu d'un plan sort de son périmètre de
lecture (#610). Ses sérialiseurs (`apps/search/serializers_fiche.py`) sont donc
**écrits à la main, sans réutiliser ceux de `apps.plans`** : en hériter ferait
entrer ici, à la première évolution de ceux-ci, des champs que personne n'aurait
décidé de publier.

Ne sortent jamais de cet endpoint :

| Exclusion | Ce que ça couvre |
|---|---|
| Budget et financement | `OperationAnnee`, `FinanceOperation`, `Operation.financeurs` |
| Ressources humaines | `Poste`, `Fonction`, `OperationAnneeRH` |
| Données empiriques | mesures d'indicateurs (`Mesure`), réalisations annuelles |
| Traçabilité interne | auteurs, dates de création et de modification |

`TestFichePubliqueCloisonnement` parcourt récursivement la charge utile et
échoue si un nom de champ contient l'un des fragments interdits (`budget`,
`etp`, `poste`, `mesure`, `realisation`, `utilisateur`…). Ajouter un champ
sensible à la fiche casse donc le test, même en le nichant profondément.

Côté interface, une tuile de résultat mène à `/exploration/plans/<slug>` avec
`?focus=<type>:<id>` : la fiche ouvre l'enjeu contenant l'objet trouvé et le
souligne. Sans cela, arriver sur un plan de deux cents objets pour en retrouver
un seul serait pénible.

### Tolérance aux fautes de frappe

La recherche combine `tsquery` et similarité trigramme par mot : `flamand`,
`flammant` ou `hydrolique` retrouvent bien « Flamant rose » et « régime
hydrologique ». Le seuil `pg_trgm` par défaut (0,6) laisse toutefois passer les
fautes qui suppriment une syllabe entière (`flamnt`).

---

## Commandes

```bash
# Reconstruire l'index de tous les plans indexables
docker compose exec web python manage.py rebuild_search_index

# Un plan en particulier (répétable)
docker compose exec web python manage.py rebuild_search_index --plan 42

# Repartir d'un index vide (après évolution des extracteurs)
docker compose exec web python manage.py rebuild_search_index --purge
```

À lancer après une reprise de données, une évolution des extracteurs, ou pour
rattraper un plan dont l'indexation automatique aurait échoué. La commande est
idempotente.

---

## Facettes et référentiels associés

| Facette de la maquette | Source |
|---|---|
| Zone géographique | `area_ids` — départements **et** régions, cf. [NOMENCLATURES.md § Découpage administratif](NOMENCLATURES.md) |
| Organismes gestionnaires | `organisme_ids` — gestionnaires des sites du plan (`cor_ep_og`) |
| Types d'aires protégées | `type_site_codes` — nomenclature `Espace naturel` (RNN, RNR, PNR, ENS…) |
| Enjeux : écologiques / socio-économiques | `sous_type` d'une ligne `enjeu` (`ecologique` / `socioeco`) |
| Indicateurs : état / pression / réponse | `sous_type` d'une ligne `indicateur` (nomenclature `TYPE_INDICATEUR`) |
| Objectifs : opérationnels / à long terme | `type_contenu` (`objectif_op` / `objectif_lt`) |
| Actions de gestion | `sous_type` d'une ligne `action` (nomenclature `CATEGORIE_ACTION_RESERVE` : SP, CS, EI, IP…) |
| Statut du plan de gestion | `statut_pg` + `annee_debut` / `annee_fin` (« en cours » = plan validé dont l'année courante est dans la période) |

---

## Ajouter un type de contenu à l'index

1. Écrire un extracteur `_documents_<type>(plan, facettes, contexte_branche)`
   dans `apps/search/indexing.py`, sur le modèle des existants.
2. L'ajouter au tuple `EXTRACTEURS` (les enjeux doivent rester en premier :
   ils alimentent `contexte_branche` pour toute la branche).
3. Ajouter la constante de type dans `ContenuIndexe.TYPE_CHOICES`.
4. `rebuild_search_index --purge` pour reconstruire.

---

## Tests

`backend/tests/apps/search/test_indexation.py` — cycle de vie, extraction par
type, comportement de recherche (radicalisation, accents, titres vs élargi) et
facettes.

```bash
docker compose exec web pytest tests/apps/search/ -v
```
