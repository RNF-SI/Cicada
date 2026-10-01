# Banc de test de l'installateur (VM Multipass)

Rejoue une installation du paquet `.deb` sur un système **neuf**, comme un
opérateur, puis vérifie que l'instance fonctionne. Le formulaire web est piloté
par son API (`POST :4567/api/install`), donc sans navigateur : un scénario se
lance d'une commande et rend un bilan OK/KO.

```bash
cd packaging/vm-bench
./bench.sh list                                   # scénarios disponibles
./bench.sh run fresh-dockerdb                     # Debian 12 par défaut
./bench.sh run external-db-localhost --os debian13 --keep
./bench.sh run upgrade --from-deb ~/cicada_0.1.47_amd64.deb   # mise à jour depuis un paquet publié
./bench.sh run external-db-remote --manuel        # tout prêt, vous remplissez le formulaire
./bench.sh shell                                  # entrer dans la VM (état du dernier run)
./bench.sh base --role tracking                   # préparer une VM (cicada, db, hub, tracking)
./bench.sh clean [--all]                          # arrêter / supprimer les VM
```

Prérequis hôte : `multipass` (snap) avec KVM, `dpkg-deb`. Compter ~4 CPU,
6 Go de RAM et 30 Go de disque par OS testé.

## Ce que fait un run

1. **Paquet** : construit le `.deb` depuis l'arbre courant (`build-deb.sh`),
   ou prend celui passé par `--deb` (ex. l'artefact de la CI).
2. **VM de base** (une par OS, construite au premier run puis figée dans
   l'instantané `socle`) : OS cloud officiel + dépôt Docker configuré comme le
   décrit #221 + images Docker de la version pré-téléchargées. Chaque run
   **restaure** ce socle : on repart d'un système propre en ~30 s.
3. **Dans la VM** (`guest/run-scenario.sh`) :
   - simule un serveur `degraded` (une unité systemd en échec, cas courant en
     production — `--no-degraded` pour s'en passer) ;
   - lance une **fausse API de suivi** et bloque la vraie : un banc ne doit
     jamais enregistrer d'instance en production. Elle sert aussi à vérifier
     que l'installateur s'enregistre et que le heartbeat part. Les services y
     sont dirigés par `Environment=TRACKING_API_URL` (surcharge systemd), sans
     toucher `/etc/cicada/cicada.conf` : c'est un conffile, le modifier ferait
     poser une question à dpkg lors d'une mise à jour ;
   - prérequis propres au scénario (PostgreSQL hôte…) ;
   - `apt install ./cicada.deb`, puis le formulaire ;
   - contrôles : services systemd, conteneurs, frontend, `/api/health/` via le
     frontend, connexion du super-admin, référentiels importés, verrouillage de
     l'installateur, + contrôles propres au scénario.
4. **Résultats** dans `results/<date>-<scénario>-<os>/` : `run.log` (déroulé),
   `results.tsv` (un contrôle par ligne), `diagnostic.txt` (état systemd,
   `docker ps`, logs web/db, `.env` aux secrets masqués, appels reçus par la
   fausse API de suivi).

Un contrôle en échec n'arrête pas le scénario : on veut la liste complète des
problèmes d'une installation, pas seulement le premier.

## Scénarios

| Scénario | Situation | Issues |
|---|---|---|
| `fresh-dockerdb` | serveur neuf, base PostGIS en conteneur (topologie du staging) | #222, #226, #234 |
| `external-db-remote` | **topologie RNF** : PostgreSQL + PostGIS sur une 2ᵉ VM (« serveur de base », avec une base GeoNature déjà présente). L'admin de la base lance la commande affichée par le formulaire ; test de connexion avant/après ; refus d'installer tant que la base n'est pas prête | #223, #269 |
| `tracking` | **serveur TrackingCicada** (VM « tracking ») : vraie API de suivi (`tracking-api/`, déployée selon son `INSTALLATION.md`) + dépôt APT signé (`packaging/apt-repo/`). `apt install cicada` depuis le dépôt (guide, étape 1), enregistrement, heartbeat et timer nocturne, publication d'une nouvelle version, bouton « Mettre à jour » → updater (apt + Docker), heartbeat suivant | #226 |
| `federation` | **de A à Z, 3 VM** : base sur un serveur séparé + hub d'exploration déployé selon `docs/DEPLOIEMENT_HUB.md` (image GHCR, compose de prod, Apache, `enroler_instance`). Jetons saisis dans le formulaire, relais activé ; refus de publier sans consentement, puis publication, plans reçus par le hub, recherche de l'instance servie par le hub avec la provenance | #636 |
| `external-db-localhost` | PostgreSQL sur le serveur CICADA lui-même, `localhost` saisi : refus immédiat et expliqué, rien de démarré (cas non pris en charge) | #223 |
| `upgrade` | installe `--from-deb` (ancien paquet, ex. l'artefact CI 0.1.47), crée des données, puis `dpkg -i` du paquet testé comme sur le staging et la prod : redéploiement, images, migrations, données conservées | #222 |
| `behind-apache` | Apache de l'hôte devant CICADA + « GeoNature » sur `:8000` : vhost de l'ancien guide (consigné) puis vhost du guide actuel (contrôlé) | #231 |
| `remove` | installation standard puis `apt remove` : plus aucun conteneur, volume de la base conservé | — |

Ajouter un scénario : un fichier `scenarios/<nom>.sh` avec une ligne
`# DESCRIPTION:` et la fonction `scenario_db_answers` (fragment JSON des
champs base de données du formulaire) ; facultativement `scenario_prereqs`,
`before_form` (après le paquet, avant le formulaire) et `scenario_checks`.
Les helpers `record`, `check`, `wait_for`, `app_sql`… sont dans `guest/lib.sh`.

Une ligne `# TRACKING_VM: oui` ajoute la VM « tracking » (API de suivi + dépôt
APT) : le paquet y est construit en deux versions dont les images existent
(`TRACKING_FROM_VERSION`, défaut 0.1.47, puis celle de `version.txt`), avec
l'URL de suivi du banc gravée dedans. Le scénario déclenche la publication de
la seconde en créant `rdv-publier`.

Une ligne `# HUB_VM: oui` ajoute une 3ᵉ VM « hub », déployée et l'instance
enrôlée avant le scénario ; les jetons arrivent dans `BENCH_HUB_URL`,
`BENCH_HUB_PUSH`, `BENCH_HUB_READ` (et sont affichés en mode `--manuel`).

Variables qu'un scénario peut poser : `INITIAL_DEB` (paquet installé en premier,
cf. `upgrade`), `EXPECT_REFUSAL` (texte du refus attendu du formulaire,
scénario négatif). Une ligne `# DB_VM: oui` lui donne une 2ᵉ VM « serveur de
base » ; sa fonction `db_server_prepare` s'y exécute au moment où le scénario
crée `attente-base` dans `before_form`, et ce qu'elle écrit dans `base-prete`
lui est remis (ex. le mot de passe affiché par le script de préparation).

## Limites connues

- Multipass ne propose que des images Ubuntu : les images Debian officielles
  (`genericcloud`) sont téléchargées dans `images/` et lancées depuis le
  fichier. `multipass clone` échoue sur ces VM, d'où les instantanés — et donc
  des scénarios **séquentiels** pour un même OS.
- Avec le pré-téléchargement (défaut), Docker est déjà installé dans le socle :
  le scénario ne vérifie plus que le paquet tire Docker par ses dépendances.
  `--no-prepull` (avec `base --rebuild`) pour couvrir ce point.
- Scénario `upgrade` : quand le premier paquet est l'ancien, ses défauts
  connus sont consignés en `INFO` (préfixe « [paquet initial] ») ; seuls les
  contrôles de la mise à jour et du paquet testé comptent dans le bilan.
- Plusieurs runs en parallèle (OS différents) : construire le paquet une fois
  et le passer par `--deb`, sinon les builds se marchent dessus dans `build/`.
- Les images Docker testées sont celles publiées sur GHCR pour la version de
  `version.txt` : le banc teste le **paquet** courant, pas un backend local.
