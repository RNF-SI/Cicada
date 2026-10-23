# Connexion par un GeoNature / UsersHub

Issues : #689 (connexion), #691 (organismes), #764 (vérification par la base UsersHub).

Une instance CICADA a **un seul mode de connexion**, choisi à l'installation (`AUTH_PROVIDER`) — jamais deux en parallèle :

| `AUTH_PROVIDER` | Qui se connecte | Inscription, mot de passe oublié, changement de mot de passe |
|---|---|---|
| `local` (défaut) | comptes CICADA (email + mot de passe) | ouverts |
| `geonature` | comptes d'un GeoNature / UsersHub, **uniquement** (cas de RNF) | fermés (403), masqués dans l'interface |

En mode `local`, l'instance ne lit jamais UsersHub.

**Comment CICADA vérifie un compte** : il lit la base UsersHub (en général celle de GeoNature), **en lecture seule**, comme pypnusershub le fait pour GeoNature, et ne laisse entrer que les comptes qui ont un profil sur **l'application CICADA** dans UsersHub. GeoNature lui-même n'est jamais appelé : ni sa version ni sa disponibilité n'entrent en jeu. Détail : [Vérification par la base UsersHub](#verification-par-la-base-usershub).

## Prérequis

- Une application CICADA déclarée dans UsersHub (son **code**, colonne `code_application`, librement choisi), et un profil sur cette application pour les groupes ou les comptes qui doivent entrer.
- Une adresse email sur chaque compte UsersHub.
- Un compte de lecture sur le serveur de la base UsersHub, créé par `cicada-usershub-lecture` ([ci-dessous](#verification-par-la-base-usershub)).

## Réglages

Deux façons de les poser (#769) :

- **depuis l'interface** — *Administration › Paramètres › Connexion* (super admin) : champs, commande du compte de lecture à copier, bouton « Tester », bouton « Activer ». Rien à éditer ni à redémarrer sur le serveur CICADA : les réglages sont gardés en base (`ccd_commons.t_connexion_geonature`, mot de passe chiffré avec une clé dérivée de la `SECRET_KEY`, jamais renvoyé par l'API) et relus à chaque connexion ;
- **par l'installeur ou le `.env`** (section « Mode de connexion »), écrits dans `/var/lib/cicada/.env`.

**Précédence.** Le **mode** choisi à l'écran (« Activer » / « Revenir aux comptes CICADA ») prime sur `AUTH_PROVIDER` : l'installeur écrit toujours `AUTH_PROVIDER=local`, l'écran n'aurait sinon jamais d'effet. Les **autres réglages** viennent du `.env` quand ils y sont renseignés (autre chose que la valeur par défaut) : le champ est alors grisé à l'écran, et une saisie est refusée (409 `valeur_environnement`). Pour les régler à l'écran, retirer la variable du `.env` et recréer les conteneurs.

**Garde-fous de l'activation** : refusée si le test échoue (400 `test_echoue`, avec une cause lisible — mot de passe refusé, ligne `pg_hba.conf` manquante, port filtré…) ou si le super admin qui active ne pourrait pas se connecter lui-même (409 `enfermement`) ; confirmation demandée quand des comptes actifs seront refusés (409 `confirmation_requise`). Connexion déjà active : une modification des réglages est testée avant d'être enregistrée. Activation et retour sont journalisés (historique d'activité, visibilité « système »).

**Secours** : `python manage.py connexion_locale` (`sudo docker exec cicada_prod_web python manage.py connexion_locale`) remet les comptes CICADA sans redémarrage, en gardant les réglages UsersHub.

API (super admin) : `GET`/`PATCH /api/auth/connexion-geonature/`, `POST …/tester/`, `…/activer/` (`{confirmer}`), `…/desactiver/` (`{confirmer}`).

Variables du `.env` :

| Variable | Rôle |
|---|---|
| `AUTH_PROVIDER` | `local` ou `geonature` |
| `GEONATURE_AUTH_LIBELLE` | nom affiché sur la page de connexion : « RNF » → « Identifiant RNF » |
| `GEONATURE_AUTH_ORGANISMES_EXCLUS` | `id_organisme` UsersHub qui ne sont pas de vrais organismes (« Autre », « ALL », tests), séparés par des virgules |
| `GEONATURE_AUTH_TIMEOUT` | délai de connexion à la base UsersHub, en secondes (défaut 10) |
| `GEONATURE_AUTH_CODE_APPLICATION`, `USERSHUB_DB_*` | application CICADA et base UsersHub : voir [Vérification par la base UsersHub](#verification-par-la-base-usershub) |

Après modification : `docker compose up -d web`.

`AUTH_PROVIDER=geonature` sans base UsersHub ni code d'application = **plus personne ne peut se connecter** : avertissement `authentication.W004` au démarrage, et la page de connexion répond « connexion non configurée » (503).

## Changer de mode après l'installation

Modifier `AUTH_PROVIDER` dans `/var/lib/cicada/.env` puis `docker compose up -d web`.

- **local → geonature** : les comptes existants sont retrouvés par leur **email** à la première connexion GeoNature. Ceux qui n'ont pas de compte UsersHub doivent en demander un **avec la même adresse email** ; sinon un second compte CICADA, vide, serait créé.
- **geonature → local** : les comptes créés par GeoNature n'ont pas de mot de passe CICADA ; ils passent par « Mot de passe oublié » (rouvert en mode local).
- **Changer de GeoNature** (préprod → prod) : les liens `usershub_id_role` désignent les comptes de l'**ancien** UsersHub ; dans le nouveau, un même numéro peut être une autre personne. Défaire les liens avant : `UPDATE utilisateurs.t_roles SET usershub_id_role = NULL;` (ils se refont par email). Mieux : tester la préprod GeoNature sur une instance CICADA de test, jamais sur la prod.

## Déroulé d'une connexion

1. La page de connexion demande l'identifiant et le mot de passe du compte <libellé>. Le mot de passe saisi part au **serveur** CICADA, qui le vérifie contre l'empreinte lue dans la base UsersHub ; le navigateur ne parle jamais à cette base, et le mot de passe n'est ni stocké ni journalisé.
2. CICADA lit dans la base UsersHub l'`id_role`, l'email, le nom, le droit sur l'application CICADA et la fiche de l'organisme (dont son **`uuid_organisme`**).
3. **Compte** : retrouvé par `usershub_id_role`, sinon par email, sinon créé (rôle « utilisateur », actif, sans mot de passe CICADA).
4. **Organisme** : retrouvé par `uuid_organisme`, sinon créé. Le compte y est rattaché (UsersHub fait foi).
5. CICADA délivre ses propres jetons, comme pour une connexion classique.

Rien n'est synchronisé en dehors des connexions : un organisme UsersHub apparaît dans CICADA à la première connexion d'un de ses membres, un changement d'organisme est pris en compte à la connexion suivante.

### Pourquoi l'uuid et pas l'id de l'organisme

`id_organisme` est une séquence propre à chaque base : le même organisme a un id différent dans UsersHub et dans CICADA. `uuid_organisme`, lui, est conservé quand les organismes sont repris de GeoNature. C'est la seule clé commune.

## Ce qui ne vient jamais de UsersHub

Les **droits CICADA** : rôle (admin d'organisme, rédacteur général, super admin), référents, sites, plans. Un compte créé à la connexion est un simple « utilisateur » : il voit en lecture les plans de son organisme et demande l'accès pour devenir référent.

## Comptes existants

- Un compte CICADA dont l'**email** est celui du compte UsersHub est relié à la première connexion : il garde son rôle et ses plans.
- Avec un email différent, un **second compte** serait créé. Consigne : créer le compte UsersHub avec l'email déjà utilisé dans CICADA.
- **Les personnes sans compte UsersHub ne peuvent plus se connecter** : elles doivent demander un compte UsersHub avec l'email de leur compte CICADA. Le message de refus de la page de connexion le leur dit.
- L'interface d'administration Django (`/admin/`) garde sa propre connexion par mot de passe, réservée au personnel technique.

## Cas d'erreur

| Situation | Résultat |
|---|---|
| Identifiant ou mot de passe faux | refus (401) |
| Base UsersHub injoignable, ou droits du compte de lecture insuffisants | refus (502) : **personne ne peut se connecter** tant que la base est indisponible |
| Compte UsersHub sans email | refus (403) |
| Compte UsersHub désactivé, ou sans profil sur l'application CICADA | refus (403) |
| Compte CICADA désactivé ou en attente de validation | refus (403) |
| Email déjà porté par un compte relié à un autre compte UsersHub | refus (409), à régler par un administrateur |
| Organisme absent de `bib_organismes` | connexion acceptée, organisme inchangé |
| Organisme exclu | connexion acceptée, sans organisme |

## ⚠️ Qui peut se connecter {#qui-peut-se-connecter}

Les comptes qui ont un profil sur **l'application CICADA** dans UsersHub, directement ou par un groupe (ex. `Grp_all`). Le profil choisi (Lecteur ou autre) n'importe pas : les droits dans CICADA (rôle, référents, plans) se règlent dans CICADA. Un changement de groupe ou de profil vaut dès la connexion suivante, sans redémarrage. Retirer un droit bloque les nouvelles connexions ; une session déjà ouverte reste valable jusqu'à l'expiration de son jeton (7 jours au plus).

**Pourquoi pas l'API GeoNature** (vérification retirée, #764) : `POST <API>/auth/login` ne contrôle jamais le droit sur une autre application que GeoNature lui-même. Avec pypnusershub ≤ 3.2.x, il ne contrôle même rien (bug du filtre par application : tout compte UsersHub dont le mot de passe est bon entre — constaté sur GeoNature global RNF, 3.2.2) ; avec pypnusershub ≥ 3.3.0, il contrôle le droit sur **GeoNature** (son `CODE_APPLICATION`), l'`id_application` transmis devant seulement exister. Le profil sur l'application CICADA ne servait donc à rien, et une montée de version de GeoNature pouvait retirer l'accès à une grande partie des utilisateurs du jour au lendemain. Aucune route de GeoNature ne permet de contrôler le droit sur une autre application que la sienne, et pypnusershub, bibliothèque Flask, ne s'intègre pas à Django : CICADA refait donc sa vérification.

## Vérification par la base UsersHub {#verification-par-la-base-usershub}

CICADA lit la base UsersHub (en général celle de GeoNature), **en lecture seule**, et refait ce que fait pypnusershub 3.3, mais sur son application :

1. compte retrouvé par son `identifiant` (`utilisateurs.t_roles`, hors groupes) ;
2. mot de passe vérifié : bcrypt (`pass_plus`), sinon ancien md5 (`pass`). pypnusershub réécrit un md5 juste en bcrypt ; CICADA non (lecture seule) ;
3. profil sur l'application dont le code est `GEONATURE_AUTH_CODE_APPLICATION`, porté par le compte ou par un de ses groupes (`cor_role_app_profil` + `cor_roles`) — sinon refus 403 « n'a pas accès à CICADA » ;
4. fiche de l'organisme lue dans `bib_organismes`.

**Compte de lecture** — pour lire ces tables, CICADA a besoin d'un compte **PostgreSQL** (pas d'un compte UsersHub : rien n'est à créer dans l'interface de UsersHub). Un compte à part plutôt que celui de GeoNature, qui peut tout modifier : celui-ci ne lit que quelques colonnes et ne peut rien écrire. C'est ce que fait toute application qui lit UsersHub (pypnusershub dans GeoNature utilise la connexion de GeoNature ; d'autres outils RNF passent par `postgres_fdw` avec un compte dédié). Il est créé **sur le serveur de la base UsersHub**, en root, par `cicada-usershub-lecture` (installé par le paquet, comme `cicada-prepare-db`). Le formulaire d'installation affiche la commande exacte :

```bash
# Base sur un autre serveur (cas de RNF) : le script est servi par l'installateur
curl -fsSL http://<serveur-cicada>:4567/usershub-lecture.sh | sudo bash -s -- --db geonature2db --client <ip-cicada>
# Base sur le serveur CICADA lui-même (GeoNature installé à côté)
sudo cicada-usershub-lecture --db geonature2db --docker-local
```

Le script :

- vérifie que la base contient bien les tables et colonnes UsersHub lues par CICADA, et compte les comptes actifs qui ont un profil sur l'application (`--code`, défaut `CICADA`). Il prévient si l'application n'existe pas ou si personne n'y a de profil ;
- crée le compte (`--role`, défaut `cicada_usershub`), avec `SELECT` sur les seules **colonnes** utiles : compte, empreintes du mot de passe, actif, groupes, droits par application, fiche d'organisme. Un `SELECT *`, toute autre colonne (`api_key`, `remarques`…), toute écriture sont refusés, et il le vérifie ;
- ajoute à `pg_hba.conf` une ligne pour **cette base, ce compte et ce serveur** (`--client`, ou les réseaux Docker avec `--docker-local`), puis recharge PostgreSQL **sans le redémarrer**. Il signale une ligne plus haut qui l'emporterait (`reject`, `peer`…) ;
- pour un serveur CICADA **distant** (`--client`), exige `ssl = on` et écrit une ligne `hostssl` : PostgreSQL refuse alors toute connexion en clair de ce compte (voir [Base sur un autre serveur](#base-distante)). `--sans-ssl` lève cette exigence, pour un réseau privé sûr uniquement ;
- vérifie la connexion (par l'interface Docker avec `--docker-local`, comme le feront les conteneurs), puis affiche les valeurs pour le formulaire et les lignes du `.env`.

Le script peut être relancé : il garde alors le mot de passe (`--password` pour le redéfinir). Sans accès root au serveur de base (base hébergée), `cicada-usershub-lecture --sql` affiche le SQL des droits, à lancer par l'administrateur de la base (`psql -d <base> -v role=cicada_usershub -v mdp='…' -v schema=utilisateurs`). La ligne de `pg_hba.conf` reste alors à ajouter à la main. Les colonnes accordées sont vérifiées par un test : toute colonne lue par le backend doit être accordée par le script (`packaging/tests/test_install_service.py`).

| Variable | Rôle |
|---|---|
| `GEONATURE_AUTH_CODE_APPLICATION` | `code_application` de CICADA dans `utilisateurs.t_applications` (ex. `CICADA`) |
| `USERSHUB_DB_HOST` / `USERSHUB_DB_PORT` / `USERSHUB_DB_NAME` | base UsersHub |
| `USERSHUB_DB_USER` / `USERSHUB_DB_PASSWORD` | le compte de lecture |
| `USERSHUB_DB_SSLMODE` | chiffrement de la connexion (valeurs de libpq) : `prefer` par défaut, `require` pour une base distante (écrit par l'installateur), `verify-full` pour vérifier aussi le certificat du serveur |
| `USERSHUB_DB_SSLROOTCERT` | avec `verify-ca` / `verify-full` : certificat de l'autorité, dans `/etc/cicada/usershub/` (monté en lecture seule dans le conteneur web), ex. `/etc/cicada/usershub/ca.crt` |

Réglages manquants : avertissement `authentication.W004` au démarrage, connexion refusée (503). Base injoignable ou droits du compte insuffisants : refus 502, cause journalisée (`Connexion UsersHub : …`). Le formulaire d'installation a un bouton « Tester la base UsersHub » (connexion, lecture de chaque table, existence de l'application).

### Base sur un autre serveur {#base-distante}

CICADA vérifie lui-même les mots de passe : avec une base distante, les **empreintes** (bcrypt, voire md5) passent sur le réseau. La connexion doit donc être chiffrée, des deux côtés :

- **côté PostgreSQL** : `ssl = on` (Debian l'active d'origine, avec le certificat auto-signé `ssl-cert-snakeoil`) et une ligne `hostssl` — c'est ce que fait `cicada-usershub-lecture --client` ; il refuse de continuer si `ssl` est coupé et donne les trois lignes à ajouter (`ssl`, `ssl_cert_file`, `ssl_key_file`, rechargement sans redémarrage) ;
- **côté CICADA** : `USERSHUB_DB_SSLMODE=require` — choisi automatiquement par l'installateur quand la base n'est pas sur ce serveur (champ « Chiffrement de la connexion »), et testé tel quel par le bouton « Tester la base UsersHub ». Une base distante lue en `prefer` déclenche l'avertissement `authentication.W005` au démarrage.

`require` chiffre sans vérifier l'identité du serveur. Pour la vérifier aussi (`verify-full`) : déposer le certificat de l'autorité qui a signé celui de PostgreSQL dans `/etc/cicada/usershub/ca.crt` sur le serveur CICADA, puis `USERSHUB_DB_SSLMODE=verify-full` et `USERSHUB_DB_SSLROOTCERT=/etc/cicada/usershub/ca.crt` dans le `.env` ; le nom dans `USERSHUB_DB_HOST` doit être celui du certificat.

Le serveur de base doit aussi laisser passer le port PostgreSQL **depuis le seul serveur CICADA** (pare-feu, groupe de sécurité de l'hébergeur).

### Versions testées {#versions-testees}

Le schéma `utilisateurs` est créé par les migrations de pypnusershub ; c'est sa version qui compte, pas celle de GeoNature. Chaque ligne a été vérifiée (10/2026) sur le schéma produit par les migrations de cette version : `cicada-usershub-lecture`, connexion en TLS depuis un autre serveur, droit direct et par un groupe, bcrypt et md5, refus (sans droit, désactivé, connexion en clair), `verifier_usershub`.

| GeoNature / UsersHub | pypnusershub | |
|---|---|---|
| GeoNature 2.13.4 | 1.6.11 | ✅ |
| GeoNature 2.14.2 | 2.1.5 | ✅ |
| GeoNature 2.15.4 | 3.0.2 | ✅ |
| UsersHub 2.4.8 | 3.0.3 | ✅ — et sur un vrai serveur (UsersHub de test RNF, PostgreSQL 17, base `geonature2db` partagée avec GeoNature) |
| GeoNature 2.16.4 | 3.1.0 | ✅ |
| GeoNature 2.17.5 | 3.2.2 | ✅ |
| GeoNature `develop` | 3.3.1 | ✅ |

## Instances déjà en service {#instances-en-service}

**Le plus simple (#769)** : mettre à jour, puis tout faire depuis *Administration › Paramètres › Connexion* — la commande du compte de lecture y est générée, « Tester » remplace `verifier_usershub`, « Activer » remplace l'édition du `.env` et le redémarrage. La procédure en ligne de commande ci-dessous reste valable.

Jusqu'à la 0.1.63, CICADA pouvait aussi vérifier les comptes par l'API GeoNature (`GEONATURE_AUTH_SOURCE=api`, `GEONATURE_AUTH_URL`, `GEONATURE_AUTH_ID_APPLICATION`). Cette vérification est **retirée** : une instance en mode GeoNature mise à jour **sans** base UsersHub configurée n'a plus aucun moyen de connexion (avertissement `authentication.W004`, qui le signale, et refus 503). **Configurer la base avant la mise à jour**, ou juste après. Une instance en connexion locale n'est pas concernée.

Pour passer une instance en service à la vérification par la base :

1. **Dans UsersHub** : l'application CICADA existe (noter son `code_application`) et les groupes qui doivent entrer y ont un profil.
2. **Sur le serveur de la base UsersHub**, créer le compte de lecture. L'installateur reste joignable après l'installation (port 4567) et sert toujours le script :
   ```bash
   curl -fsSL http://<serveur-cicada>:4567/usershub-lecture.sh | sudo bash -s -- --db <base> --client <ip-cicada>
   ```
   Sinon, copier `/usr/bin/cicada-usershub-lecture` (un seul fichier, SQL compris) sur ce serveur et le lancer avec les mêmes options.
3. **Dans `/var/lib/cicada/.env`**, ajouter les lignes affichées par le script (`GEONATURE_AUTH_CODE_APPLICATION`, `USERSHUB_DB_*`). Avant de relancer web, **vérifier** qui pourra se connecter : la commande fonctionne quel que soit le mode en service, et peut se lancer dans un conteneur temporaire qui lit le nouveau `.env` :
   ```bash
   sudo bash -c '. /usr/share/cicada/compose-files.sh && cd /usr/share/cicada && docker compose $(compose_files_args) --env-file /var/lib/cicada/.env run --rm --no-deps --entrypoint python web manage.py verifier_usershub'
   ```
   La commande lit la base UsersHub et liste les comptes CICADA actifs qui seront **refusés** : pas de compte UsersHub (ni par son id, ni par son email), compte désactivé, ou pas de profil sur l'application. Elle indique aussi combien de super-utilisateurs pourront se connecter. Donner les profils manquants dans UsersHub, puis relancer la commande. Codes retour : 0 = personne n'est refusé, 1 = des comptes seraient refusés, 2 = base injoignable.
4. **Relancer web** :
   ```bash
   sudo bash -c '. /usr/share/cicada/compose-files.sh && cd /usr/share/cicada && docker compose $(compose_files_args) --env-file /var/lib/cicada/.env up -d web'
   ```
   Tester avec un compte qui a le profil (200), puis avec un compte qui ne l'a pas (« n'a pas accès à CICADA »). Les anciennes lignes `GEONATURE_AUTH_URL`, `GEONATURE_AUTH_ID_APPLICATION` et `GEONATURE_AUTH_SOURCE` peuvent être supprimées. Les comptes CICADA ne sont pas touchés : le lien `usershub_id_role` est le même.

Parcours rejoué sur le banc VM (`packaging/vm-bench`, scénario `usershub-base`) : GeoNature et sa base sur le serveur CICADA, compte créé par le script, test du formulaire, installation, puis vraies connexions (profil par un groupe, md5, droit GeoNature seul, aucun droit, compte désactivé, base arrêtée → 502).

## ⚠️ Limites — solution transitoire, cible : Keycloak (#690)

Cicada ne peut pas utiliser pypnusershub directement : c'est une bibliothèque **Flask**, liée à l'application GeoNature, inutilisable dans Django. Cicada refait donc la vérification en lisant la base UsersHub, ce qui a un coût :

- **Un accès à la base UsersHub** : compte de lecture, ligne `pg_hba.conf`, port ouvert depuis le serveur CICADA (une fois, à l'installation).
- **Dépendance au schéma `utilisateurs`** : tables et colonnes lues (vérifiées de pypnusershub 1.6 à 3.3, [Versions testées](#versions-testees)). À revérifier quand une version de pypnusershub modifie ce schéma.
- **Le mot de passe transite par le serveur Cicada**, qui le compare à l'empreinte. Avec Keycloak (OpenID Connect), la personne le saisit sur la page du fournisseur d'identité et Cicada ne le voit jamais.
- **Pas de session partagée** : se connecter à GeoNature ne connecte pas à Cicada, et inversement.

La cible est un **fournisseur d'identité standard (Keycloak, OpenID Connect, #690)**, qui lève ces limites. Le rattachement compte / organisme posé ici (`usershub_id_role`, uuid d'organisme) sera réutilisé : seul le moyen de vérifier l'identité changera. Il suffira d'ajouter un mode `AUTH_PROVIDER=oidc`.

## Mise en place sur l'instance RNF

Avant d'activer la connexion, réaligner les 4 organismes créés à la main dans CICADA qui doublonnent un organisme UsersHub : `scripts/rnf/2026-10-realignement-uuid-organismes.sql` (hors dépôt ; une seule fois). C'est un bloc `DO` unique, utilisable depuis DBeaver comme depuis psql : lancé tel quel (`appliquer := false`), il affiche le rapport avant/après puis s'interrompt sur « SIMULATION terminée » sans rien écrire ; passer `appliquer := true` après relecture. Sans ce réalignement, la première connexion d'un agent RNF créerait un second « Réserves Naturelles de France » et lui ferait perdre l'accès aux plans de son organisme.

**En service depuis le 15/10/2026** (réalignement appliqué le 14/10), par l’API GeoNature, puis par la base UsersHub (bascule du 23/10/2026) :

| Réglage | Valeur |
|---|---|
| `GEONATURE_AUTH_CODE_APPLICATION` | `CICADA` (application n° 18 ; jusqu'à la release, profil donné au seul `Grp_cicada` ; à la release, à `grp_all`) |
| `USERSHUB_DB_HOST` / `USERSHUB_DB_NAME` | `10.0.30.12` / `geonature_global` (serveur de bases du GeoNature global, GeoNature 2.17.5) |
| `USERSHUB_DB_SSLMODE` | `require` (ligne `hostssl` pour `10.0.20.13`, le serveur CICADA) |
| `GEONATURE_AUTH_LIBELLE` | `RNF` |

## Code

- `backend/apps/authentication/providers/usershub_base.py` — lecture de la base UsersHub ; `usershub.py` — rattachement compte / organisme ; commande `verifier_usershub`
- `POST /api/auth/login-geonature/`, `GET /api/auth/mode/` — `apps/authentication/views.py` ; fermeture des routes locales : `ConnexionLocaleActive` (`providers/__init__.py`) ; vérification au démarrage : `apps/authentication/checks.py`
- `Role.usershub_id_role` — migration `users/0012`
- Frontend : `features/auth/login.component.*`, `AuthService.login(…, mode)` / `getLoginMode()`, `connexionLocaleGuard` (inscription, mot de passe oublié)
- Tests : `backend/tests/integration/test_api_connexion_usershub_base.py` (vrai schéma UsersHub), `test_api_connexion_geonature.py` (mode, compte, organisme), `login.component.spec.ts` ; installateur : `packaging/tests/test_install_service.py`
