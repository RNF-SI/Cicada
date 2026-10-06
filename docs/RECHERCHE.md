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

## Volume et choix du moteur

Le raisonnement ci-dessus a été **vérifié par la mesure**, sur un index
synthétique de **1 300 000 documents** — l'ordre de grandeur attendu une fois les
~4 400 plans repris — avec la DDL et les index réels, et la forme de requête
exacte de `filtrer_contenus()` / `trier_contenus()`.

Machine : conteneur de développement (16 cœurs, 30 Go), PostgreSQL **non réglé**
(`shared_buffers` 128 Mo), `work_mem` porté à 64 Mo. Index : 3,6 Go au total dont
613 Mo d'index.

| Cas | Correspondances | Temps |
|---|---:|---:|
| Mot moyennement fréquent (`orchidee`) | 47 k | **195 ms** |
| Faute de frappe (`flamand`, 0 correspondance plein texte) | — | **190 ms** |
| Mode élargi (`search_full`) | 111 k | 880 ms |
| Pagination profonde (page 5) | 47 k | 188 ms |
| Mot très fréquent (`habitat`, 65 % du corpus) | 848 k | 1 500 ms |
| Idem, **sans** le `OR` trigramme | 848 k | 455 ms |
| Compteurs d'onglets sur ce même mot | 848 k | 1 450 ms |

**Conclusion : le volume n'est pas le problème.** Une recherche réaliste — celle
qui renvoie un nombre de résultats exploitable — répond en ~200 ms sur une base
non réglée, sous le seuil de bascule de 300 ms.

Les deux cas lents ne sont pas des limites de PostgreSQL mais des **choix de
conception**, qu'Elasticsearch ne corrigerait pas magiquement :

1. **Le repli trigramme est appliqué inconditionnellement.** `titre %> mot` est
   `OR`é à *chaque* requête, ce qui triple le coût du pire cas (1 500 ms contre
   455 ms sans lui) : le bitmap déborde de `work_mem` et repasse en mode *lossy*,
   forçant une revérification page entière. Or ce repli n'a d'intérêt que quand la
   recherche exacte ne rend rien ou presque. Le déclencher **en second temps**
   supprimerait le coût et améliorerait la pertinence.
2. **Les compteurs d'onglets sont exacts.** Ils imposent un agrégat sur
   l'intégralité du jeu de résultats. C'est une décision produit, et elle coûte
   le même prix dans n'importe quel moteur.

Elasticsearch garde un avantage réel et mesurable sur un point : il sait
interrompre le parcours des listes d'occurrences pour un *top-k* (block-max
WAND), là où PostgreSQL doit calculer `ts_rank` sur **toutes** les
correspondances. Cet avantage ne joue que sur les termes très fréquents — ceux
dont la liste de résultats n'est de toute façon pas exploitable par un humain.

À mettre en face : un service JVM (~2 Go de RAM) à packager, sauvegarder et
migrer sur **chaque** installation Debian client, et un index qui peut diverger
silencieusement de la base.

**Décision : rester sur PostgreSQL.** Avant d'envisager une bascule, épuiser dans
l'ordre :

1. conditionner le repli trigramme à un premier passage exact infructueux ;
2. régler PostgreSQL (`work_mem`, `shared_buffers`) — le banc tournait aux
   valeurs par défaut ;
3. évaluer l'extension **RUM**, qui stocke l'information de rang *dans* l'index
   et supprime donc l'accès au tas pour le tri — c'est-à-dire exactement
   l'avantage d'Elasticsearch, sans quitter PostgreSQL.

Enfin, la fédération multi-instances (#636) **ne change pas ce calcul** : les
~4 400 plans sont l'univers *total*, réparti entre instances. Un portail qui les
agrège tous représente le corpus mesuré ici, pas un multiple.

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
| Texte | `titre`, `rattachements`, `description`, `contexte`, `enfants` | Ce qui est recherché |
| Affichage | `chemin`, `enjeu_slug`, `parent_type`, `parent_libelle`, `sous_type`, `sous_type_libelle` | Tuile de résultat et lien vers l'écran réel |
| Facettes | `statut_pg`, `annee_debut`, `annee_fin`, `annees_extension`, `site_ids`, `organisme_ids`, `type_site_codes`, `area_ids` | Filtres + compteurs |
| Vecteurs | `search_titre`, `search_description`, `search_contexte`, `search_enfants`, `search_full` | Colonnes **générées** par PostgreSQL |

Seules les données nécessaires au **filtrage et aux compteurs** sont
dénormalisées. Les libellés d'affichage (nom du plan, du site, du gestionnaire
principal) sont joints à la volée : une page ne montre que 10 à 20 résultats, et
une donnée jointe ne peut pas devenir obsolète.

### Les vecteurs de recherche et la portée (#681 / #686)

Ce sont des **colonnes générées** : elles ne peuvent pas diverger du texte
indexé, et aucune étape Python ne peut être oubliée.

L'ancien interrupteur « rechercher dans les titres uniquement » était compris
de travers (#686) : il mélangeait plusieurs axes. Il est remplacé par **trois
axes indépendants**, que l'utilisateur coche dans la barre latérale
(`?portee=description,parents,enfants`) :

| Toujours interrogé | `search_titre` — libellé (poids A) **et objets rattachés** (poids B) : « ce que l'objet est et porte » |
|---|---|
| ☐ aussi dans les descriptions | `search_description` |
| ☐ aussi dans les éléments parents | `search_contexte` — libellés de **toute** l'ascendance (enjeu, objectif, niveau d'exigence…) + métriques, suivi, code |
| ☐ aussi dans les éléments enfants | `search_enfants` — libellés de toute la descendance (#682) : un enjeu ressort quand l'un de ses objectifs porte le mot |

Seuls `search_titre` et `search_full` (la réunion de tout) portent un index
GIN. Une combinaison intermédiaire est servie par l'index de `search_full`
(sur-ensemble) puis **revérifiée exactement** sur la concaténation des
vecteurs demandés (`filters.vecteur_de_portee`) : huit index, un par
combinaison, coûteraient des centaines de Mo pour rien.

`titres_seulement=false` reste compris comme « les trois axes » : une URL de
recherche est faite pour être partagée.

La configuration plein texte est `public.french_unaccent` : le dictionnaire
`french` radicalise (`limicoles` → `limicol`) mais ne retire pas les accents, si
bien que « foret » ne trouverait pas « forêt ». On chaîne donc `unaccent` avant
`french_stem`.

### Les « rattachements » : espèces, habitats, protocoles… (#634)

La colonne `rattachements` porte les objets de référentiel attachés à l'objet
**ou à l'enjeu dont il descend**, actions comprises :

| Rattachement | Source |
|---|---|
| Espèces | `CorEnjeuTaxon` — nom scientifique **et** nom vernaculaire, `SuiviInventaire.taxon_taxref` |
| Habitats | `CorEnjeuHabitat` (`lb_hab_fr` + `cd_hab`), `SuiviInventaire.habitat_ref` |
| Éléments géologiques | `CorEnjeuGeologie`, `CorIndicateurGeologie` (nom + `id_inpg`) |
| Protocoles standardisés | `SuiviInventaire.protocoles` — `nom_protocole` et `protocole_campanule_nom` |
| Référence PressRef | `Pression.id_type_pression` (nomenclature `TYPE_PRESSION`) et `id_pressref` |
| Catégorie et type d'action | `CATEGORIE_ACTION_RESERVE` et `TYPE_ACTION` |

Ces rattachements étant dans `search_titre`, chercher « STOC » remonte les
actions qui **appliquent** ce protocole et pas seulement celles qui le nomment ;
chercher « Bécasseau variable » marche aussi bien que « Calidris alpina » ; et
une espèce fait ressortir les enjeux **et les actions** qui la concernent.

Une action retrouve l'enjeu dont elle hérite via son indicateur ou via une de
ses métriques (`_Branche.enjeu_par_indicateur` dans `indexing.py`).

### Le « contexte » et la recherche élargie

La colonne `contexte` porte, pour chaque objet, **les libellés de ses ancêtres**
— l'enjeu dont il descend, son objectif, son facteur d'influence. Les objets de
référentiel, eux, sont dans `rattachements` (ci-dessus) et non ici.

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

Côté interface, une tuile d'un plan **distant** (reçu par le hub, #636) mène à
`/exploration/plans/<instance:slug>` avec `?focus=<type>:<id>&q=<mot>` : la
fiche ouvre l'enjeu contenant l'objet trouvé, le souligne et surligne le mot.

### Les écrans réels (#683)

Pour un plan **de cette base**, une tuile n'ouvre plus la fiche publique mais
l'**écran réel** du plan : la fiche action pour une action
(`/plans/<slug>/enjeux/operations/<id>/fiche`), l'arborescence ouverte sur la
branche et l'objet pour le reste (`/plans/<slug>/enjeux/<enjeu_slug>#olt-<id>`),
la page du plan à défaut. Le mot cherché voyage dans `?q=` et y est surligné
(`SurlignerDirective`). Chaque tuile dit ce que le clic ouvre (`acces_direct`,
posé par l'instance — ou par son relais quand le hub répond, lui ne sachant pas
qui le lit).

Ces écrans s'ouvrent à tout utilisateur connecté pour un plan validé, grâce à
la **lecture d'exploration** de `apps/plans/exploration.py` : le périmètre de
lecture (#610) est élargi aux plans validés sur les seules actions de lecture
d'un objet ou « par parent », et la réponse est **élaguée** de ses clés
sensibles (`CLES_SENSIBLES` : mesures, réalisations, budget, RH, financement,
fichiers, personnes) quand le lecteur n'est là que par l'exploration. Elle
porte alors `acces_exploration: true`, ce qui fait masquer côté interface les
entrées Suivis / Exports / Paramétrage, les sections Utilisateurs et Documents
du plan, et Programmation / Réalisation de la fiche action. Les listes « à
plat » et les ViewSets de suivi ne sont pas touchés ; les écritures restent
soumises aux permissions habituelles. Verrouillé par
`tests/apps/plans/test_lecture_exploration.py`.

### Dire pourquoi un résultat est là (#650, #681, #682)

Une tuile montre l'**arborescence** qui mène à l'objet retrouvé (`chemin`,
de l'enjeu au parent direct — niveau d'exigence et résultat attendu compris,
bien qu'ils ne soient pas explorables), l'objet lui-même mis en avant, et le
mot surligné **partout où il apparaît** : titre, maillons de l'arbre, extraits.
Pour chaque champ interrogé mais non affiché (espèce rattachée, description,
contexte, enfant), l'API renvoie un **extrait** découpé par `ts_headline`
autour de la correspondance (`extraits`), sans balisage — le surlignage se
fait par segments côté interface, jamais par injection de HTML.

En repli approximatif (#651), `ts_headline` ne trouve rien et le mot retenu
n'est pas celui qui a été tapé : `surlignage.py` recalcule la similarité
trigramme pour la page affichée et renvoie les mots à surligner
(`termes_surlignes` : « flamand » → « Flamant »).

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
| Statut du plan de gestion | `statut_pg` + `annee_debut` / `annee_fin` / `annees_extension` (« en cours » = plan validé dont l'année courante est dans la période, prolongation comprise — #676) |

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
