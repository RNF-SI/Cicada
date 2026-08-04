# Test local de la fédération de l'exploration

Ce document décrit comment faire tourner **plusieurs instances CICADA sur une
seule machine** et vérifier qu'un contenu ajouté sur l'une remonte bien dans
l'exploration centralisée. Il accompagne l'issue **#636**, qui recense les
limites de la fédération et les décisions restant à prendre.

C'est un **banc d'essai**, pas une architecture de production. Ce qui est
volontairement rudimentaire est signalé comme tel.

---

## Les trois briques

| Brique | Rôle | Interface | API | `CICADA_INSTANCE_ID` |
|---|---|---|---|---|
| **RNF** | instance de production d'un gestionnaire | http://localhost | http://localhost:8000 | `rnf` |
| **CEN** | seconde instance, base indépendante | http://localhost:8081 | http://localhost:8001 | `cen` |
| **Portail** | exploration centralisée | http://localhost:8082 | http://localhost:8002 | `portail` |

Le portail est **une instance CICADA comme les autres**. Il réutilise donc telle
quelle la page d'exploration et son API — ce qui est justement l'intérêt de la
topologie « index central » : le portail n'est pas un logiciel de plus à écrire,
c'est le même logiciel dont l'index est alimenté autrement.

Il n'a aucun plan de gestion à lui. Son index est rempli par ce que RNF et CEN
publient.

---

## Démarrer

L'instance RNF est le stack habituel, inchangé :

```bash
docker compose up -d
```

Les deux autres réutilisent le même `docker-compose.yml`, plus un override et un
fichier d'environnement :

```bash
# Instance CEN
docker compose -p cicada_cen --env-file .env.cen \
  -f docker-compose.yml -f docker-compose.instance.yml up -d

# Portail
docker compose -p cicada_portail --env-file .env.portail \
  -f docker-compose.yml -f docker-compose.instance.yml up -d
```

Puis, sur chaque instance métier, des données de test :

```bash
docker exec cicada_cen_web python manage.py seed_testdata
docker exec cicada_cen_web python manage.py rebuild_search_index --purge
```

> `rebuild_search_index --purge` est nécessaire après avoir donné son identité à
> une instance : les documents déjà indexés portent l'identifiant qu'ils avaient
> à l'indexation.

### Ce que l'override corrige

Trois choses seulement empêchaient de lancer le `docker-compose.yml` deux fois :

1. **les `container_name` figés** (`cicada_db`, `cicada_web`…) — les noms de
   conteneurs sont globaux à Docker, contrairement aux volumes et aux réseaux qui
   sont déjà préfixés par le nom de projet ;
2. **le sous-réseau figé** (`172.30.0.0/16`) — deux projets ne peuvent pas le
   réclamer en même temps (`Pool overlaps with other one on this address space`) ;
3. **les ports publiés**, déjà paramétrables, qu'il suffisait de décaler.

Ajouter une quatrième instance ne demande donc qu'un nouveau fichier
d'environnement avec un `INSTANCE_PREFIX`, un `INSTANCE_SUBNET` et des ports
libres.

> Chaque instance importe ses propres référentiels au premier démarrage. Les
> fichiers d'environnement fournis mettent `TAXREF_IMPORT_OPTS=--lite` (~8 000
> taxons au lieu de ~700 000) : sans ça, chaque nouvelle instance repart pour un
> import complet.

---

## Synchroniser le portail

```bash
docker exec cicada_portail_web python manage.py pull_federation \
  --source http://host.docker.internal:8001      # depuis le CEN
docker exec cicada_portail_web python manage.py pull_federation \
  --source http://host.docker.internal:8000      # depuis RNF
```

`--dry-run` récupère et compte sans rien écrire.

Les instances se joignent par `host.docker.internal` (leur port publié sur
l'hôte) parce que chaque projet Docker Compose a son propre réseau : le portail
ne peut pas résoudre le nom `web` d'un autre projet. En production, ce serait
simplement l'URL publique de l'instance.

### Une synchronisation par état, pas par événement

Chaque exécution récupère **tout** l'index publié par la source, puis supprime
les documents de cette instance qui n'ont pas été revus. C'est ce qui rend la
dépublication fiable : un plan repassé en brouillon, supprimé, ou une instance
décommissionnée disparaissent du portail sans qu'aucun message de retrait n'ait
eu à être reçu.

Un index qui se contenterait de rejouer des événements finirait immanquablement
par laisser visible un plan que son gestionnaire a dépublié — un incident, pas
une gêne.

---

## Le test de bout en bout

C'est le scénario qui justifie tout le reste : *un ajout côté CEN doit remonter
dans l'exploration centralisée.*

1. **Côté CEN** — ajouter un enjeu à un plan en brouillon, puis valider le plan.
   La validation déclenche l'indexation (`apps/search/signals.py`) ; un brouillon
   n'est jamais explorable.
2. **Côté portail** — vérifier que la recherche ne le trouve pas encore.
3. **Synchroniser** — `pull_federation --source http://host.docker.internal:8001`.
4. **Côté portail** — la recherche le trouve, attribué à l'instance `cen`, avec
   le nom du plan, son gestionnaire et ses sites, alors que ce plan n'existe pas
   dans la base du portail.
5. **Retrait** — repasser le plan en brouillon côté CEN, resynchroniser :
   le document disparaît du portail.

Ces invariants sont couverts par
`backend/tests/apps/search/test_federation.py` (22 tests).

---

## Ce que ce banc d'essai démontre — et ce qu'il ne résout pas

### Le problème central : rien n'est identifiant entre instances

`id_pg`, `id_objet`, `id_site`, `id_organisme`, `id_area`, le `slug` d'un plan et
même `uuid_organisme` (tiré par `uuid4()` à la création **locale**) sont propres à
chaque base. Le plan n° 42 de RNF n'a aucun rapport avec le plan n° 42 du CEN.

Le banc d'essai le montre sans détour : les deux instances sont seedées avec les
mêmes fixtures, donc leurs documents portent **les mêmes `id_objet`**. Sans
`instance_id` dans la clé d'unicité, ingérer la seconde écraserait la première.

### Trois traitements selon qu'une clé stable existe

| Facette | Clé | Traitement |
|---|---|---|
| Type d'aire protégée | mnémonique (`RNN`, `RNR`…) | transmise telle quelle ✅ |
| Statut du plan | chaîne (`valide`…) | transmise telle quelle ✅ |
| Zone géographique | `l_areas.area_code` (INSEE) | publiée en **codes**, re-résolue en identifiants locaux à l'arrivée ✅ |
| Sites | `t_espace_protege.id_inpn`, national mais *nullable* | publiés en **codes INPN**, re-résolus — mais seulement si le destinataire connaît le site ⚠️ |
| Organismes gestionnaires | aucune | **vidée** ⚠️ |

Les zones fonctionnent parce que le découpage administratif vient du même
référentiel national partout : seuls les identifiants techniques diffèrent, pas
les codes.

La ligne « organismes » est volontairement **vidée plutôt que recopiée**.
Recopier un identifiant local ferait matcher un document distant sur le mauvais
organisme — une corruption silencieuse. Un tableau vide produit une absence
visible : le document ne ressort simplement pas quand on filtre par organisme.
Tant que l'identité nationale des organismes n'est pas tranchée (#636), c'est le
seul comportement défendable.

### Pourquoi les sites ne se généralisent pas aussi bien que les zones

Les sites sont désormais publiés en **codes INPN** — `id_inpn` est unique et
national — et re-résolus en identifiants locaux à l'ingestion, exactement comme
les zones. L'identifiant local ne quitte jamais l'instance émettrice.

Mais l'analogie s'arrête là, et la mesure sur le banc d'essai le montre : sur
les 96 documents que le portail ingère de RNF, **96 rattachent leurs zones et
aucun ne rattache ses sites**. La raison est structurelle — `l_areas` est un
*référentiel national*, importé au démarrage de **chaque** instance ; les sites
sont de la *donnée métier*. Un portail qui n'héberge aucun plan n'a aucun site
en base, donc rien à quoi apparier les codes reçus.

La résolution fonctionne bel et bien dès que le destinataire connaît le site :
ingérés par le CEN plutôt que par le portail, les mêmes 96 documents rattachent
tous leur site, celui de la Camargue chez RNF retombant sur celui du CEN par son
code INPN. C'est le cas de la **co-gestion**, et c'est celui qui compte pour le
dédoublonnage inter-instances (limite n° 3 de #636).

Pour que la facette « site » serve aussi sur un portail sans données propres, il
faudrait **stocker les codes INPN dans l'index** et filtrer dessus, plutôt que
de les traduire en identifiants locaux — le traitement déjà appliqué aux types
d'aire protégée. C'est une colonne de plus et un filtre à réécrire ; ce n'est
pas fait.

> À noter : `site_ids` n'est aujourd'hui **lu par personne**. `filtrer_contenus`
> n'expose pas de filtre « site » et l'interface n'en propose pas. La colonne est
> alimentée et indexée, mais aucune requête ne s'en sert — la fédération des
> sites est donc pour l'instant une fondation, pas une fonctionnalité visible.

### Non résolu ici

- **Authentification.** Un jeton partagé (`CICADA_FEDERATION_TOKEN`), suffisant
  pour tester le transport, à ne pas déployer tel quel. Dépend de #514 (OAuth2 /
  OIDC).
- **Identité nationale des organismes.** Décision de maîtrise d'ouvrage
  (SIRET ? annuaire RNF ?), pas un problème technique.
- **Doublons inter-instances.** Deux instances peuvent légitimement porter le
  même site, voire le même plan. Rien ne dédoublonne aujourd'hui.
- **Fiche d'un plan distant.** La tuile de résultat s'affiche correctement, mais
  ouvrir la fiche complète d'un plan hébergé ailleurs n'est pas traité.
- **Gouvernance de la publication.** Qui consent à publier, et à quelle maille
  (instance, organisme, plan) ? C'est le vrai sujet de #636.

---

## Arrêter

```bash
docker compose -p cicada_cen --env-file .env.cen \
  -f docker-compose.yml -f docker-compose.instance.yml down          # -v pour purger les données
docker compose -p cicada_portail --env-file .env.portail \
  -f docker-compose.yml -f docker-compose.instance.yml down
```

---

## Volume et choix du moteur de recherche

La question « faut-il passer à Elasticsearch vu les ~4 400 plans à reprendre ? »
a été tranchée par la mesure, pas par principe. Le détail est dans
[RECHERCHE.md](RECHERCHE.md#volume-et-choix-du-moteur).

Un point vaut d'être noté ici : **la fédération ne multiplie pas le volume**. Les
~4 400 plans sont l'univers *total*, réparti entre instances — le portail qui les
agrège tous représente le même corpus qu'une instance unique qui les hébergerait.
C'est précisément le cas qui a été mesuré.
