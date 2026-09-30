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
./bench.sh shell                                  # entrer dans la VM (état du dernier run)
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
     que l'installateur s'enregistre et que le heartbeat part ;
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
| `external-db-localhost` | PostgreSQL + PostGIS déjà sur le serveur ; l'opérateur saisit `localhost` et un compte existant (non superuser), sans autre commande | #223, #269 |
| `remove` | installation standard puis `apt remove` : plus aucun conteneur, volume de la base conservé | — |
| `external-db-guide` | PostgreSQL hôte préparé en suivant `docs/INSTALLATION_GUIDE.md` à la lettre (`listen_addresses`, `pg_hba` 172.17, `cicada-prepare-db`) | #223 |

Ajouter un scénario : un fichier `scenarios/<nom>.sh` avec une ligne
`# DESCRIPTION:` et la fonction `scenario_db_answers` (fragment JSON des
champs base de données du formulaire) ; facultativement `scenario_prereqs`,
`before_form` (après le paquet, avant le formulaire) et `scenario_checks`.
Les helpers `record`, `check`, `wait_for`, `app_sql`… sont dans `guest/lib.sh`.

## Limites connues

- Multipass ne propose que des images Ubuntu : les images Debian officielles
  (`genericcloud`) sont téléchargées dans `images/` et lancées depuis le
  fichier. `multipass clone` échoue sur ces VM, d'où les instantanés — et donc
  des scénarios **séquentiels** pour un même OS.
- Avec le pré-téléchargement (défaut), Docker est déjà installé dans le socle :
  le scénario ne vérifie plus que le paquet tire Docker par ses dépendances.
  `--no-prepull` (avec `base --rebuild`) pour couvrir ce point.
- Les images Docker testées sont celles publiées sur GHCR pour la version de
  `version.txt` : le banc teste le **paquet** courant, pas un backend local.
