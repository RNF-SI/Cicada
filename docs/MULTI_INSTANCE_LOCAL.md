# Banc d'essai de l'exploration fédérée

Ce document décrit comment faire tourner **deux instances CICADA et le hub
d'exploration sur une seule machine**, et vérifier qu'un contenu ajouté sur
l'une remonte bien dans l'exploration de l'autre. Il accompagne l'issue **#636**,
qui recense les limites et les décisions restant à prendre.

C'est un **banc d'essai**, pas une architecture de production. Ce qui est
volontairement rudimentaire est signalé comme tel.

---

## Les trois briques

| Brique | Rôle | Interface | API | Identité |
|---|---|---|---|---|
| **RNF** | instance CICADA | http://localhost | http://localhost:8000 | `rnf` |
| **CEN** | instance CICADA, base indépendante | http://localhost:8081 | http://localhost:8001 | `cen` |
| **Hub** | back d'exploration, **sans interface** | — | http://localhost:8002 | `hub` |

Le hub n'est **pas** une instance CICADA. C'est un projet distinct
([`hub/`](../hub/README.md)) qui ne connaît aucun modèle métier : ni
`PlanGestion`, ni `Enjeu`, ni `Operation`. Il ne stocke que deux tables — les
plans publiés et leurs objets explorables — plus la fiche rendue de chaque plan.

À terme l'index de recherche ne vit plus dans CICADA du tout : chaque instance
produit ses documents et les dépose ici, et c'est ici que la recherche s'exécute.
Le temps de la transition, les deux coexistent.

---

## Le sens des flux

```
   ┌──────────┐   ① dépôt de l'état complet   ┌─────────┐
   │ CICADA   │ ────────────────────────────► │         │
   │ RNF      │ ◄──────────────────────────── │   HUB   │
   └──────────┘   ② recherche + fiche          │  (API)  │
   ┌──────────┐                                │         │
   │ CICADA   │ ────────────────────────────►  │         │
   │ CEN      │ ◄──────────────────────────── │         │
   └──────────┘                                └─────────┘
```

C'est l'instance qui **va vers** le hub, et non l'inverse. Ce n'est pas un détail
de plomberie : une instance derrière un pare-feu ou sans adresse publique peut
publier, alors qu'elle ne peut pas être interrogée.

Le navigateur, lui, ne parle jamais au hub. L'exploration continue d'appeler le
backend de son instance, qui relaie — le jeton reste côté serveur, il n'y a ni
CORS ni second domaine à déclarer, et la bascule est invisible pour le frontend.

---

## Démarrer — la version courte

```bash
scripts/federation.sh up --open # les trois briques, puis les 2 interfaces dans Chrome
scripts/federation.sh push      # les deux instances déposent leur index
scripts/federation.sh check     # la recherche est-elle bien transverse ?
```

`--open` (ou `scripts/federation.sh open` seul) ouvre **deux fenêtres distinctes**
sur `/exploration` : l'intérêt du banc est de comparer les deux instances côte à
côte, pas de basculer entre deux onglets. Les sessions ne se marchent pas dessus
— les deux instances sont sur des ports différents, donc des origines
différentes, et le navigateur leur donne chacune son `localStorage`. On peut donc
être connecté aux deux en même temps, y compris sous des comptes différents.

`scripts/federation.sh` (sans argument) liste tout ce qu'il sait faire :
`status`, `reindex`, `mode local|hub`, `logs`, `test`, `reset-hub`, `down`.

Le script existe parce que chacune des trois briques se lance avec des arguments
qu'on ne retape pas juste, et parce que trois pièges se paient cher à
rediagnostiquer — il les traite tout seul :

- le hub **doit** être lancé avec son nom de projet, faute de quoi son service
  `db` détruit et recrée le conteneur de la base de l'instance principale ;
- une base ayant vu la branche avant la renumérotation porte
  `0004_federation_instance_id` et bloque au démarrage sur « column instance_id
  already exists » — le script réaligne l'enregistrement ;
- changer l'identité d'une instance périme tout son index, et la publication
  échoue alors (franchement, mais après coup) : `reindex` fait le `--purge`.

Ce qui suit détaille ce que le script fait, pour les cas où il faut sortir des
rails.

---

## Démarrer — à la main

### Le hub

```bash
cp .env.hub.example .env.hub        # adapter si des ports sont pris
docker compose -f docker-compose.hub.yml --env-file .env.hub up -d
```

L'API répond sur http://localhost:8002/api/health/. Le hub importe au démarrage
`ref_geo` et les nomenclatures depuis **les fichiers source de CICADA**, montés
en lecture seule : les documents voyagent en codes et sont re-résolus ici, deux
fichiers divergents produiraient des zones introuvables en silence.

### Les instances

L'instance RNF est le stack habituel, inchangé :

```bash
docker compose up -d
```

La seconde réutilise le même `docker-compose.yml`, plus un override et un
fichier d'environnement :

```bash
docker compose -p cicada_cen --env-file .env.cen \
  -f docker-compose.yml -f docker-compose.instance.yml up -d
```

Puis, sur chaque instance, des données de test et un index :

```bash
docker exec cicada_cen_web python manage.py seed_testdata
docker exec cicada_cen_web python manage.py rebuild_search_index --purge
```

> `--purge` est nécessaire après avoir donné son identité à une instance : les
> documents déjà indexés portent l'identifiant qu'ils avaient à l'indexation.
> La commande de dépôt refuse d'ailleurs de publier si elle ne trouve aucun
> document sous l'identité courante, en nommant celle qu'elle a trouvée.

### Ce que l'override corrige

Trois choses seulement empêchaient de lancer le `docker-compose.yml` deux fois :

1. **les `container_name` figés** (`cicada_db`, `cicada_web`…) — les noms de
   conteneurs sont globaux à Docker, contrairement aux volumes et aux réseaux qui
   sont déjà préfixés par le nom de projet ;
2. **le sous-réseau figé** (`172.30.0.0/16`) — deux projets ne peuvent pas le
   réclamer en même temps (`Pool overlaps with other one on this address space`) ;
3. **les ports publiés**, déjà paramétrables, qu'il suffisait de décaler.

Ajouter une instance ne demande donc qu'un fichier d'environnement avec un
`INSTANCE_PREFIX`, un `INSTANCE_SUBNET` et des ports libres.

> ⚠️ `docker-compose.hub.yml` fige `name: cicada_hub`. Sans ce nom de projet,
> Compose le déduit du dossier — « cicada » — et le service `db` du hub **détruit
> puis recrée le conteneur de la base de l'instance principale**. Le volume
> survit, mais l'instance tombe.

> Chaque instance importe ses propres référentiels au premier démarrage. Les
> fichiers d'environnement fournis mettent `TAXREF_IMPORT_OPTS=--lite` (~8 000
> taxons au lieu de ~700 000) : sans ça, chaque nouvelle instance repart pour un
> import complet.

---

## Configurer la fédération

Côté hub (`.env.hub`), un jeton **par instance** — révoquer l'accès d'une
instance compromise ne doit pas interrompre la publication des autres :

```bash
HUB_FEDERATION_TOKENS=rnf:jeton-rnf,cen:jeton-cen
HUB_READ_TOKEN=jeton-lecture
```

Côté instance (`.env`, `.env.cen`) :

```bash
CICADA_INSTANCE_ID=cen
CICADA_PUBLIC_URL=http://localhost:8081
CICADA_HUB_URL=http://host.docker.internal:8002
CICADA_HUB_PUSH_TOKEN=jeton-cen
CICADA_HUB_READ_TOKEN=jeton-lecture
CICADA_EXPLORATION_SOURCE=local     # `hub` pour basculer la recherche
```

Les instances joignent le hub par `host.docker.internal` — chaque projet Compose
a son propre réseau, le nom de service `hub` n'est pas résolvable depuis
ailleurs. En production ce serait l'URL publique du hub.

> `CICADA_INSTANCE_ID` doit être **non vide**. Une identité vide s'écrit dans
> chaque ligne d'index, où elle passe inaperçue, et plus aucune publication ne
> retrouve ensuite ces documents.

---

## Publier

```bash
docker exec cicada_cen_web python manage.py push_federation
docker exec cicada_web     python manage.py push_federation
```

`--dry-run` construit les charges utiles sans rien envoyer. `--sans-fiche`
accélère le dépôt au prix des fiches distantes. `--page-size` règle la taille des
pages : elle est petite par défaut (10 plans) parce que chaque plan emporte sa
fiche rendue, qui mobilise plusieurs centaines d'objets.

### Une publication en trois temps

`ouvrir un lot` → `déposer N pages` → `basculer`.

À la bascule, le hub retire les plans de cette instance qui n'étaient pas dans le
lot. C'est ce qui rend la dépublication fiable : un plan repassé en brouillon,
supprimé, ou une instance décommissionnée disparaissent sans qu'aucun message de
retrait n'ait eu à être émis ni à survivre au réseau.

Mais purger « ce qui n'a pas été revu » suppose d'avoir **tout** reçu : une
coupure au milieu d'un envoi viderait sinon le hub de ce qui n'était pas encore
arrivé. D'où le lot. En cas d'échec la commande l'abandonne plutôt que de le
basculer — entre « incomplet » et « périmé », c'est périmé qui est récupérable.

La purge est **bornée à l'instance du lot**, et l'instance émettrice est déduite
du **jeton** et non du corps de la requête. Sans ces deux bornes, un jeton valide
suffirait à ouvrir un lot au nom d'une autre instance puis à le basculer —
c'est-à-dire à purger son index.

---

## Basculer l'exploration sur le hub

```bash
CICADA_EXPLORATION_SOURCE=hub
```

L'instance cesse de lire son index local et relaie vers le hub. Même URL, même
forme de réponse : le frontend ne voit pas la différence, et le retour arrière
est un simple réglage.

Il n'y a **pas de repli** sur l'index local si le hub est injoignable : la
requête rend un 502 explicite. Un repli silencieux servirait les résultats de
cette seule instance sous une interface qui promet une recherche transverse, et
l'utilisateur conclurait que les plans des autres organismes n'existent pas.

---

## Le test de bout en bout

C'est le scénario qui justifie tout le reste. Il a été déroulé, voici ce qu'il
donne :

| Étape | Observé |
|---|---|
| RNF publie | 22 plans, 96 documents |
| CEN publie | 22 plans, 96 documents |
| Index agrégé | 44 plans, 192 documents, compteurs d'onglets doublés |
| Ajout d'un enjeu côté CEN, republication | 97 documents, le nouvel enjeu remonte attribué à `cen` |
| Plan repassé en brouillon côté CEN, republication | 21 plans, `1 plan dépublié`, sa fiche en **404** |
| Le plan de **même slug** chez RNF | intact, **200** |

Cette dernière ligne est l'invariant à ne jamais casser : une instance ne
dépublie qu'elle-même.

### Ce que le banc d'essai démontre au passage

Les deux instances sont seedées des mêmes fixtures, et produisent donc des
**slugs identiques pour des plans différents** :

```
bac-a-sable-plan-initial-2010-2020  →  cen (id_pg=30), rnf (id_pg=1864)
```

Sans `instance_id` dans les clés d'unicité, ingérer le second écraserait le
premier — silencieusement. C'est aussi pourquoi un plan se désigne par
`instance:slug` et non par son seul slug.

Ces invariants sont couverts par `hub/tests/` (55 tests) et
`backend/tests/apps/search/` (140 tests).

---

## Ce que ce banc d'essai ne résout pas

### Le problème central : rien n'est identifiant entre instances

`id_pg`, `id_objet`, `id_site`, `id_organisme`, `id_area`, le `slug` d'un plan et
même `uuid_organisme` (tiré par `uuid4()` à la création **locale**) sont propres à
chaque base. Le plan n° 42 de RNF n'a aucun rapport avec le plan n° 42 du CEN.

Trois traitements en découlent, selon qu'une clé stable existe ou non :

| Facette | Clé | Traitement |
|---|---|---|
| Type d'aire protégée | mnémonique (`RNN`, `RNR`…) | transmis tel quel ✅ |
| Statut du plan | chaîne (`valide`…) | transmis tel quel ✅ |
| Zone géographique | `l_areas.area_code` (INSEE) | publiée en **codes**, re-résolue au hub ✅ |
| Sites | `t_espace_protege.id_inpn`, national mais *nullable* | publiés en **codes INPN**, stockés tels quels ⚠️ |
| Organismes gestionnaires | aucune | **nom seulement**, pour l'affichage ⚠️ |

Les zones fonctionnent parce que le découpage administratif vient du même
référentiel national partout : seuls les identifiants techniques diffèrent.

Les sites sont désormais **stockés en codes INPN** côté hub, et non traduits en
identifiants locaux : le hub n'hébergeant aucun site, il n'a rien à quoi les
apparier. Réserve propre aux sites : `id_inpn` est *nullable*, un site qui n'en
porte pas n'est pas publiable. La liste transmise dit « ces sites-là », jamais
« seulement ceux-là ».

La ligne « organismes » est la seule où **aucune** clé n'existe. Leur nom voyage
pour l'affichage, mais la colonne de filtrage reste vide : recopier un
identifiant local ferait matcher le mauvais organisme — une corruption
silencieuse — là où un tableau vide produit une absence visible. Le filtre est
écrit et testé dans cet état, pour que le jour où l'identité nationale sera
tranchée, seule l'ingestion soit à toucher.

### Non résolu

- **Authentification.** Des jetons partagés, suffisants pour tester le
  transport, à ne pas déployer tels quels. Dépend de #514 (OAuth2 / OIDC).
- **Identité nationale des organismes.** Décision de maîtrise d'ouvrage
  (SIRET ? annuaire RNF ?), pas un problème technique.
- **Doublons inter-instances.** Deux instances peuvent légitimement porter le
  même site, voire le même plan. Les codes INPN stockés au hub sont ce qui
  permettra de les rapprocher ; rien ne dédoublonne aujourd'hui.
- **Fraîcheur des fiches.** Une fiche est un instantané, qui vieillit jusqu'à la
  publication suivante. Acceptable parce que le contenu d'un plan validé est
  verrouillé (#248) — ce qui bouge, ce sont les libellés joints.
- **Périodicité des publications.** Rien ne les déclenche aujourd'hui : la
  commande se lance à la main. Une tâche planifiée reste à câbler.
- **Gouvernance de la publication.** Qui consent à publier, et à quelle maille
  (instance, organisme, plan) ? C'est le vrai sujet de #636.

---

## Arrêter

```bash
scripts/federation.sh down        # CEN et hub ; RNF, stack de travail, est épargné
scripts/federation.sh down rnf    # pour l'arrêter aussi
```

Soit, à la main :

```bash
docker compose -p cicada_cen --env-file .env.cen \
  -f docker-compose.yml -f docker-compose.instance.yml down     # -v pour purger
docker compose -f docker-compose.hub.yml --env-file .env.hub down
```

---

## Volume et choix du moteur de recherche

La question « faut-il passer à Elasticsearch vu les ~4 400 plans à reprendre ? »
a été tranchée par la mesure, pas par principe. Le détail est dans
[RECHERCHE.md](RECHERCHE.md#volume-et-choix-du-moteur).

Un point vaut d'être noté ici : **la fédération ne multiplie pas le volume**. Les
~4 400 plans sont l'univers *total*, réparti entre instances — le hub qui les
agrège tous représente le même corpus qu'une instance unique qui les hébergerait.
C'est précisément le cas qui a été mesuré.
