# Déploiement du hub d'exploration fédérée (#636)

Le hub est un **back API seul, sans interface**. Il agrège l'index des
instances CICADA et sert la recherche transverse. Il se déploie sur son propre
serveur, indépendamment des instances : il doit pouvoir tomber sans les
entraîner, et inversement.

- Architecture et contrat d'échange : [hub/README.md](../hub/README.md)
- Banc d'essai local (2 instances + hub) : [MULTI_INSTANCE_LOCAL.md](MULTI_INSTANCE_LOCAL.md)

## Pourquoi le hub sort du même dépôt que CICADA

Le hub vit dans le dépôt CICADA tant que le contrat d'échange n'est pas figé —
un seul commit fait alors évoluer les deux côtés. Trois choses le retiennent
aujourd'hui : `filters.py` existe **en deux exemplaires** dont la parité est
vérifiée par un test qui pilote les deux projets à la fois ; les sérialiseurs de
fiche évoluent de pair ; les référentiels nationaux sont les mêmes fichiers.

Un dépôt commun n'empêche pas un **déploiement séparé** : chaque image a son
contexte de build, sa release produit trois images (`cicada-backend`,
`cicada-frontend`, `cicada-hub`) portant le même tag, et chaque serveur ne tire
que la sienne. Le numéro de version partagé est même un avantage tant que le
contrat bouge : « quelle version du hub parle à quelle version d'instance » ne
se pose pas.

## Ce que le serveur du hub doit avoir

| | |
|---|---|
| Docker + Docker Compose v2 | le hub et sa base tournent en conteneurs |
| Apache avec `mod_proxy`, `mod_proxy_http`, `mod_headers`, `mod_ssl` | seul point d'entrée public |
| Un certificat TLS pour le nom public | le dépôt transporte des jetons |
| ~5 Go de disque | image (1,7 Go, GDAL) + index |

Il n'a **pas** besoin de PostgreSQL installé nativement, ni de Redis, ni de
Celery, ni de CICADA à côté : l'image embarque le code et les référentiels
nationaux.

## Installation

### 1. Récupérer les fichiers de déploiement

L'image est tirée depuis GHCR, mais le compose a besoin de deux fichiers du
dépôt (`docker-compose.hub.prod.yml` et `hub/docker/postgres/init.sql`, qui crée
les schémas à la première initialisation de la base).

```bash
sudo git clone --depth 1 --branch v0.1.X https://github.com/RNF-SI/Cicada.git /opt/cicada-hub
cd /opt/cicada-hub
```

### 2. Configurer

```bash
sudo cp .env.hub.prod.example .env.hub.prod
sudo chmod 600 .env.hub.prod
sudo nano .env.hub.prod    # SECRET_KEY, ALLOWED_HOSTS, mots de passe, jetons
sudo mkdir -p /var/log/cicada-hub
```

Le démarrage échoue explicitement si `SECRET_KEY`, `ALLOWED_HOSTS` ou
`POSTGRES_PASSWORD` manquent — c'est voulu : un hub qui démarre avec la clé de
développement serait pire qu'un hub qui ne démarre pas. Les jetons, eux, ne sont
pas des variables d'environnement : les instances s'enrôlent après coup avec
`enroler_instance` (voir plus bas).

### 3. Démarrer

```bash
sudo docker compose -f docker-compose.hub.prod.yml --env-file .env.hub.prod up -d
sudo docker compose -f docker-compose.hub.prod.yml --env-file .env.hub.prod logs -f hub
```

Au premier démarrage, l'entrypoint applique les migrations puis importe les deux
référentiels (`ref_geo`, nomenclatures). Les imports suivants sont ignorés si
les données sont déjà là : redémarrer un hub qui tourne depuis des mois ne coûte
pas un réimport.

Vérification :

```bash
curl -s http://127.0.0.1:8002/api/health/
# {"statut": "ok", "service": "cicada-hub", "instance": "hub"}
```

## Apache

```apache
<VirtualHost *:443>
    ServerName hub.cicada.example.org

    SSLEngine on
    SSLCertificateFile      /etc/letsencrypt/live/hub.cicada.example.org/fullchain.pem
    SSLCertificateKeyFile   /etc/letsencrypt/live/hub.cicada.example.org/privkey.pem

    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"

    ProxyPass        / http://127.0.0.1:8002/
    ProxyPassReverse / http://127.0.0.1:8002/

    # Le dépôt d'un lot envoie des pages de plans avec leur fiche JSON
    # complète : ni la taille ni la durée par défaut ne suffisent.
    LimitRequestBody 104857600
    ProxyTimeout 300

    ErrorLog  ${APACHE_LOG_DIR}/cicada-hub-error.log
    CustomLog ${APACHE_LOG_DIR}/cicada-hub-access.log combined
</VirtualHost>
```

Quatre pièges :

1. **Ne pas réécrire `/api`.** Le hub sert *tout* sous `/api/` et il n'y a aucun
   frontend à servir à côté. Un `ProxyPass /api/ …` mal aligné produit des 404
   qui ressemblent à un hub vide.
2. **Ne pas filtrer les en-têtes custom.** L'authentification passe par
   `X-Federation-Token` (dépôt) et `X-Hub-Token` (lecture). Apache les
   transmet par défaut ; un WAF ou un `RequestHeader unset` trop large les
   coupe, et l'erreur ressemble à une révocation de jeton.
3. **`ALLOWED_HOSTS` doit contenir le `ServerName`.** Avec `ProxyPreserveHost
   On`, Django voit le nom public : s'il n'est pas déclaré, tout répond 400.
4. **Taille du corps.** Django refuse par défaut tout corps > 2,5 Mo, y compris
   en JSON. Le réglage `DATA_UPLOAD_MAX_MEMORY_SIZE` et le `LimitRequestBody`
   d'Apache doivent rester cohérents. La soupape côté instance est
   `push_federation --page-size N`.

## Enrôler une instance

Une instance a besoin de **deux** jetons, distincts parce que lire n'est pas
écrire et que révoquer l'un ne doit pas emporter l'autre. Ils se délivrent
depuis le hub, sans redémarrage :

```bash
sudo docker compose -f docker-compose.hub.prod.yml --env-file .env.hub.prod \
     exec hub python manage.py enroler_instance rnf \
     --libelle "Réserves Naturelles de France" \
     --url https://cicada.rnf.example.org
```

La commande affiche les deux jetons **une seule fois** : le hub n'en conserve
que l'empreinte. Les reperdre n'est pas grave — un renouvellement coûte une
commande et une ligne à changer côté instance — mais aller les relire en base
est impossible, et c'est voulu.

```bash
enroler_instance rnf --renouveler depot   # l'ancien cesse aussitôt d'être accepté
enroler_instance rnf --desactiver         # refuse les jetons, n'efface rien
enroler_instance rnf --reactiver
enroler_instance --lister                 # le registre, et qui publie sans être enrôlé
```

Désactiver **ne dépublie pas** : l'index déjà déposé reste servi. Le retrait des
données est une décision de l'instance, qui la prend avec
`retrait_federation --confirmer` — la confondre avec une suspension d'accès
ferait disparaître des plans à la première suspicion.

> Les variables `HUB_FEDERATION_TOKENS` / `HUB_READ_TOKENS` restent acceptées en
> **amorce**, pour accueillir la première instance avant qu'un registre
> n'existe. Mais elles ne valent que pour une instance **absente du registre** :
> dès qu'une instance y figure, un jeton d'environnement portant son nom est
> refusé. Sinon un jeton révoqué en base resterait admis par une variable
> oubliée dans un fichier de déploiement.

Côté instance, dans son `.env` de production (`/var/lib/cicada/.env` pour une
installation par paquet Debian) :

```
CICADA_INSTANCE_ID=rnf
CICADA_INSTANCE_LABEL=Réserves Naturelles de France
CICADA_PUBLIC_URL=https://cicada.rnf.example.org
CICADA_HUB_URL=https://hub.cicada.example.org
CICADA_HUB_PUSH_TOKEN=<jeton de dépôt>
CICADA_HUB_READ_TOKEN=<jeton de lecture>
CICADA_EXPLORATION_SOURCE=hub
CICADA_HUB_PUSH_AUTO=true
```

> ⚠️ **`CICADA_INSTANCE_ID` est immuable.** Il s'écrit dans chaque ligne d'index
> et entre dans toutes les clés d'unicité. Le changer périme tout l'index publié
> sous l'ancienne valeur : il faut alors `rebuild_search_index --purge` côté
> instance puis republier. Le choisir court et lisible (`rnf`, `cen-aura`) : il
> apparaît dans la référence d'un plan (`rnf:camargue`). L'identifiant donné à
> `enroler_instance` et celui de l'instance **doivent être le même**.

À l'installation par paquet Debian, l'installeur web propose une section
**« Exploration fédérée »** qui écrit ces lignes. Elle est facultative et refuse
un identifiant mal formé — c'est le seul moment où l'erreur se corrige sans
conséquence.

### Suivre l'état de la fédération

```bash
curl -s -H "X-Hub-Token: <jeton-lecture>" \
     https://hub.cicada.example.org/api/federation/instances/
```

Rend, par instance : enrôlée ou non, active ou suspendue, date de la dernière
publication **réussie**, nombre de plans et de documents publiés. Aucun jeton ni
empreinte n'y figure. Une instance qui publie encore avec un jeton
d'environnement y apparaît avec `enrolee: false` — c'est la liste de ce qu'il
reste à enrôler.

## Publier depuis une instance

Rien ne part tant qu'un **super administrateur n'a pas activé le partage** dans
`/administration/parametres`. Le réglage est faux par défaut, y compris après
une montée de version : publier le contenu de ses plans est un engagement de la
structure, pas un effet de bord d'une mise à jour.

Une fois le partage activé, la publication est **automatique chaque nuit à
2h30** (tâche Celery `apps.search.tasks.publier_vers_le_hub`). Elle ne fait rien
tant que les trois conditions ne sont pas réunies — hub et jeton configurés,
`CICADA_HUB_PUSH_AUTO` vrai, partage consenti — ce qui permet de la laisser
planifiée sur toutes les instances, fédérées ou non.

Un dépôt porte l'**état complet** et non un différentiel : une nuit sautée ne
perd rien, la suivante repart de l'état courant.

À la main :

```bash
docker exec cicada_prod_web python manage.py push_federation --dry-run
docker exec cicada_prod_web python manage.py push_federation
```

En cas d'échec, la commande abandonne le lot plutôt que de le basculer : entre
« incomplet » et « périmé », c'est périmé qui est récupérable. La publication
précédente reste en place, complète.

Retrait volontaire, commande **distincte** de la publication pour que
l'accidentel ne ressemble pas au voulu (`push_federation` refuse par ailleurs un
index vide, qui dépublierait tout) :

```bash
docker exec cicada_prod_web python manage.py retrait_federation --confirmer
```

Décocher le partage dans l'interface arrête les publications à venir sans
effacer les précédentes.

## Monter de version

```bash
cd /opt/cicada-hub
sudo git fetch --tags && sudo git checkout v0.1.Y
sudo sed -i 's/^CICADA_VERSION=.*/CICADA_VERSION=0.1.Y/' .env.hub.prod
sudo docker compose -f docker-compose.hub.prod.yml --env-file .env.hub.prod pull
sudo docker compose -f docker-compose.hub.prod.yml --env-file .env.hub.prod up -d
```

Les migrations s'appliquent au démarrage. L'index n'est pas reconstruit : si une
migration change la forme des documents, les instances doivent republier.

## Recette après déploiement

```bash
# 1. Le hub répond, à travers Apache
curl -s https://hub.cicada.example.org/api/health/

# 2. Une instance publie
docker exec cicada_prod_web python manage.py push_federation

# 3. Le hub sert ce qu'elle a publié
curl -s -H "X-Hub-Token: <jeton-lecture>" \
     "https://hub.cicada.example.org/api/exploration/plans/?q=<un-nom-de-plan>"

# 4. La fiche d'un plan, désignée par instance:slug
curl -s -H "X-Hub-Token: <jeton-lecture>" \
     "https://hub.cicada.example.org/api/exploration/plans/rnf:<slug>/"

# 5. L'instance relaie bien (CICADA_EXPLORATION_SOURCE=hub) : la page
#    /exploration annonce une portée nationale et renvoie des plans des
#    autres instances. Un 502 ici est explicite et voulu — pas de repli
#    silencieux sur l'index local.
```

Ce que cette recette vérifie et que rien d'autre ne voit : la couture Apache.
En-têtes `X-Federation-Token` / `X-Hub-Token` transmis, `ALLOWED_HOSTS` aligné
sur le `ServerName`, taille et durée des dépôts.

**Le banc d'essai reste local.** `tests/federation/bench.py` pilote les briques
par `docker exec` sur des noms de conteneurs figés (`cicada_web`,
`cicada_hub_api`) : les variables `BENCH_*_API` ne déplacent que la partie HTTP.
Il ne peut donc pas viser un hub déployé sur un autre hôte. C'est lui qui couvre
le contrat et la **parité des 14 requêtes** entre les deux `filters.py` — à
lancer avant de tagger, pas après avoir déployé :

```bash
scripts/federation.sh test          # suites unitaires (hub + CICADA)
scripts/federation.sh test --bench  # contrat, scénarios, parité (3 stacks locaux)
```

Le test qui manque encore, et qu'aucun des deux niveaux ne donne : un
`push_federation` à **volume réel**. C'est là que `LimitRequestBody`,
`ProxyTimeout` et `DATA_UPLOAD_MAX_MEMORY_SIZE` se révèlent — un banc à quelques
plans de test ne les atteindra jamais. À faire sur le staging, avec une base
restaurée depuis une instance réelle.

## Ne pas lancer le compose de production sur un poste de développement

`docker-compose.hub.prod.yml` porte le même `name:` et les mêmes noms de
conteneurs et de volume que le compose de développement : le lancer sur une
machine où tourne le banc d'essai **remplace** le hub de dev et réutilise sa
base. Le nom de projet figé reste indispensable (sans lui, Compose le déduit du
dossier — « cicada » — et le service `db` détruit le conteneur de la base de
l'instance principale), mais il fait de ces deux fichiers deux façons de piloter
le même stack, pas deux stacks.
