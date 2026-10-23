# Connexion par un GeoNature / UsersHub

Issues : #689 (connexion), #691 (organismes).

Une instance CICADA a **un seul mode de connexion**, choisi à l'installation (`AUTH_PROVIDER`) — jamais deux en parallèle :

| `AUTH_PROVIDER` | Qui se connecte | Inscription, mot de passe oublié, changement de mot de passe |
|---|---|---|
| `local` (défaut) | comptes CICADA (email + mot de passe) | ouverts |
| `geonature` | comptes d'un GeoNature / UsersHub, **uniquement** (cas de RNF) | fermés (403), masqués dans l'interface |

En mode `local`, l'instance n'appelle jamais GeoNature.

**Ce que Cicada appelle** : l'API du **GeoNature**, jamais l'application UsersHub. `POST <API>/auth/login` est fournie par pypnusershub (le module d'authentification de UsersHub, embarqué dans GeoNature) ; `GET <API>/users/organism/<id>` par GeoNature. Les comptes et organismes lus sont ceux des tables UsersHub (schéma `utilisateurs`) que GeoNature partage.

## Prérequis

- **GeoNature 2.17.0 ou plus récent.** Cette version ajoute `GET <API>/users/organism/<id>` (fiche d'un organisme) et impose `pypnusershub >= 3.2.0`, qui accepte le jeton en `Authorization: Bearer`. Avec une version plus ancienne, la connexion fonctionne mais le compte n'est **pas** rattaché à son organisme.
- Une application CICADA déclarée dans UsersHub (son `id_application`).

## Réglages

Proposés par l'installeur (section « Mode de connexion »), écrits dans `/var/lib/cicada/.env` :

| Variable | Rôle |
|---|---|
| `AUTH_PROVIDER` | `local` ou `geonature` |
| `GEONATURE_AUTH_URL` | adresse de l'**API** GeoNature = la valeur `API_ENDPOINT` de sa configuration (ex. `https://geonature.exemple.fr/api` derrière Apache ; `http://127.0.0.1:5000` en développement) |
| `GEONATURE_AUTH_ID_APPLICATION` | `id_application` de CICADA dans UsersHub |
| `GEONATURE_AUTH_LIBELLE` | nom affiché sur la page de connexion : « RNF » → « Identifiant RNF » |
| `GEONATURE_AUTH_ORGANISMES_EXCLUS` | `id_organisme` UsersHub qui ne sont pas de vrais organismes (« Autre », « ALL », tests), séparés par des virgules |
| `GEONATURE_AUTH_TIMEOUT` | délai des appels à GeoNature, en secondes (défaut 10) |

Après modification : `docker compose up -d web`.

`AUTH_PROVIDER=geonature` sans `GEONATURE_AUTH_URL` ni `GEONATURE_AUTH_ID_APPLICATION` = **plus personne ne peut se connecter** : avertissement `authentication.W002` au démarrage, et la page de connexion répond « connexion non configurée » (503).

## Changer de mode après l'installation

Modifier `AUTH_PROVIDER` dans `/var/lib/cicada/.env` puis `docker compose up -d web`.

- **local → geonature** : les comptes existants sont retrouvés par leur **email** à la première connexion GeoNature. Ceux qui n'ont pas de compte UsersHub doivent en demander un **avec la même adresse email** ; sinon un second compte CICADA, vide, serait créé.
- **geonature → local** : les comptes créés par GeoNature n'ont pas de mot de passe CICADA ; ils passent par « Mot de passe oublié » (rouvert en mode local).
- **Changer de GeoNature** (préprod → prod) : les liens `usershub_id_role` désignent les comptes de l'**ancien** UsersHub ; dans le nouveau, un même numéro peut être une autre personne. Défaire les liens avant : `UPDATE utilisateurs.t_roles SET usershub_id_role = NULL;` (ils se refont par email). Mieux : tester la préprod GeoNature sur une instance CICADA de test, jamais sur la prod.

## Déroulé d'une connexion

1. La page de connexion demande l'identifiant et le mot de passe du compte <libellé>. Le mot de passe saisi part au **serveur** CICADA, qui le relaie à GeoNature (`POST <API>/auth/login`) ; le navigateur ne parle jamais à GeoNature, et le mot de passe n'est ni stocké ni journalisé.
2. GeoNature renvoie l'`id_role`, l'email, le nom et l'`id_organisme` de la personne.
3. Avec le jeton reçu, CICADA lit la fiche de l'organisme (`GET <API>/users/organism/<id>`) pour obtenir son **`uuid_organisme`**. Le jeton n'est pas conservé.
4. **Compte** : retrouvé par `usershub_id_role`, sinon par email, sinon créé (rôle « utilisateur », actif, sans mot de passe CICADA).
5. **Organisme** : retrouvé par `uuid_organisme`, sinon créé. Le compte y est rattaché (UsersHub fait foi).
6. CICADA délivre ses propres jetons, comme pour une connexion classique.

Rien n'est synchronisé en dehors des connexions : un organisme UsersHub apparaît dans CICADA à la première connexion d'un de ses membres, un changement d'organisme est pris en compte à la connexion suivante.

### Pourquoi l'uuid et pas l'id de l'organisme

`id_organisme` est une séquence propre à chaque base : le même organisme a un id différent dans GeoNature et dans CICADA. `uuid_organisme`, lui, est conservé quand les organismes sont repris de GeoNature. C'est la seule clé commune.

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
| GeoNature injoignable | refus (502) : **personne ne peut se connecter** tant que GeoNature est indisponible |
| Compte UsersHub sans email | refus (403) |
| Compte CICADA désactivé ou en attente de validation | refus (403) |
| Email déjà porté par un compte relié à un autre compte UsersHub | refus (409), à régler par un administrateur |
| Organisme illisible (panne, GeoNature < 2.17) | connexion acceptée, organisme inchangé, erreur journalisée |
| Organisme exclu | connexion acceptée, sans organisme |

## ⚠️ Qui peut se connecter {#qui-peut-se-connecter}

Ça dépend de la façon dont les comptes sont vérifiés (`GEONATURE_AUTH_SOURCE`, #764) :

| Source | Qui entre | Ce qui est vérifié |
|---|---|---|
| **`base`** (recommandé) | les comptes qui ont un profil sur **l'application CICADA** dans UsersHub, directement ou par un groupe (ex. Grp_all) | CICADA lit la base UsersHub lui-même ([ci-dessous](#verification-par-la-base-usershub)) |
| `api`, GeoNature avec **pypnusershub ≤ 3.2.x** | **tout compte UsersHub** dont le mot de passe est bon, quels que soient ses droits | rien : bug du filtre par application (requête corrélée qui ne garde qu'une condition toujours vraie). Constaté sur GeoNature global RNF (3.2.2) |
| `api`, GeoNature avec **pypnusershub ≥ 3.3.0** (20/10/2026) | les comptes qui ont un droit sur **GeoNature lui-même** (son `CODE_APPLICATION`, ex. `GNG`) | le droit sur l'application CICADA n'est **jamais** lu : `id_application` doit seulement exister |

Par l'API, le profil sur l'application CICADA dans UsersHub ne sert donc **à rien**, et le passage de GeoNature à pypnusershub 3.3 peut retirer l'accès à une grande partie des utilisateurs du jour au lendemain (RNF : 249 comptes avec un droit sur GNG, ~920 sur CICADA). Aucune route de GeoNature ne permet de contrôler le droit sur une autre application que la sienne : d'où la source `base`.

## Vérification par la base UsersHub {#verification-par-la-base-usershub}

`GEONATURE_AUTH_SOURCE=base` : CICADA lit la base UsersHub (en général celle de GeoNature), **en lecture seule**, et refait ce que fait pypnusershub 3.3, mais sur son application :

1. compte retrouvé par son `identifiant` (`utilisateurs.t_roles`, hors groupes) ;
2. mot de passe vérifié : bcrypt (`pass_plus`), sinon ancien md5 (`pass`). pypnusershub réécrit un md5 juste en bcrypt ; CICADA non (lecture seule) ;
3. profil sur l'application dont le code est `GEONATURE_AUTH_CODE_APPLICATION`, porté par le compte ou par un de ses groupes (`cor_role_app_profil` + `cor_roles`) — sinon refus 403 « n'a pas accès à CICADA » ;
4. fiche de l'organisme lue dans `bib_organismes`. La suite (compte et organisme CICADA) est la même qu'avec l'API.

GeoNature n'intervient plus : ni sa version, ni sa disponibilité. `GEONATURE_AUTH_URL` et `GEONATURE_AUTH_ID_APPLICATION` sont ignorés.

**Compte de lecture** — créé **sur le serveur de la base UsersHub**, en root, par `cicada-usershub-lecture` (installé par le paquet, comme `cicada-prepare-db`). Le formulaire d'installation affiche la commande exacte :

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
| `GEONATURE_AUTH_SOURCE` | `base` |
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

**Une mise à jour ne change rien.** Sans `GEONATURE_AUTH_SOURCE` dans le `.env`, la source reste `api`, comme avant. Aucune action n'est donc obligatoire, mais le défaut de contrôle reste en place (voir [Qui peut se connecter](#qui-peut-se-connecter)). Une instance en connexion locale n'est pas concernée.

Pour passer une instance en service à la vérification par la base, sans couper la connexion :

1. **Dans UsersHub** : l'application CICADA existe (noter son `code_application`) et les groupes qui doivent entrer y ont un profil.
2. **Sur le serveur de la base UsersHub**, créer le compte de lecture. L'installateur reste joignable après l'installation (port 4567) et sert toujours le script :
   ```bash
   curl -fsSL http://<serveur-cicada>:4567/usershub-lecture.sh | sudo bash -s -- --db <base> --client <ip-cicada>
   ```
   Sinon, copier `/usr/bin/cicada-usershub-lecture` (un seul fichier, SQL compris) sur ce serveur et le lancer avec les mêmes options.
3. **Dans `/var/lib/cicada/.env`**, ajouter les lignes affichées par le script (`GEONATURE_AUTH_CODE_APPLICATION`, `USERSHUB_DB_*`), **sans toucher encore à `GEONATURE_AUTH_SOURCE`**, puis relancer web :
   ```bash
   sudo bash -c '. /usr/share/cicada/compose-files.sh && cd /usr/share/cicada && docker compose $(compose_files_args) --env-file /var/lib/cicada/.env up -d web'
   ```
   La source restant `api`, rien ne change pour les utilisateurs.
4. **Vérifier avant de basculer** :
   ```bash
   docker exec cicada_prod_web python manage.py verifier_usershub
   ```
   La commande lit la base UsersHub et liste les comptes CICADA actifs qui seraient **refusés** une fois la bascule faite : pas de compte UsersHub (ni par son id, ni par son email), compte désactivé, ou pas de profil sur l'application. Elle indique aussi combien de super-utilisateurs pourront encore se connecter. Donner les profils manquants dans UsersHub, puis relancer la commande. Codes retour : 0 = personne n'est refusé, 1 = des comptes seraient refusés, 2 = base injoignable.
5. **Basculer** : `GEONATURE_AUTH_SOURCE=base` dans le `.env`, puis relancer web (même commande). Tester avec un compte qui a le profil (200), puis avec un compte qui ne l'a pas (« n'a pas accès à CICADA »).
6. **Retour arrière** : `GEONATURE_AUTH_SOURCE=api` et relancer web. Les comptes CICADA ne sont pas touchés : le lien `usershub_id_role` est le même dans les deux sources.

Parcours rejoué sur le banc VM (`packaging/vm-bench`, scénario `usershub-base`) : GeoNature et sa base sur le serveur CICADA, compte créé par le script, test du formulaire, installation, puis vraies connexions (profil par un groupe, md5, droit GeoNature seul, aucun droit, compte désactivé, base arrêtée → 502).

## ⚠️ Limites — solution transitoire, cible : Keycloak (#690)

Cicada ne peut pas utiliser pypnusershub directement : c'est une bibliothèque **Flask**, liée à l'application GeoNature, inutilisable dans Django. Cicada passe donc soit par la base UsersHub (source `base`), soit par les **requêtes HTTP de l'API GeoNature** (source `api`), ce qui a un coût (les deux premiers points ne concernent que l'API) :

- **Dépendance à la disponibilité de GeoNature** : GeoNature arrêté ou en maintenance = plus personne ne se connecte à Cicada (le mode est exclusif).
- **Dépendance à la version et au format de l'API** : routes `/auth/login` et `/users/organism/<id>`, forme de la réponse, comportement en cas de refus (redirection 302 sans `Accept: application/json`). Rien de cela n'est un contrat public : une mise à jour de GeoNature peut casser la connexion. À revérifier à chaque montée de version de GeoNature (essai contre la préprod).
- **Pas de contrôle d'accès par application** (voir plus haut) : tout compte GeoNature entre.
- **Le mot de passe transite par le serveur Cicada** : la personne le saisit dans Cicada, qui le relaie. Avec Keycloak (OpenID Connect), elle le saisit sur la page du fournisseur d'identité et Cicada ne le voit jamais.
- **Pas de session partagée** : se connecter à GeoNature ne connecte pas à Cicada, et inversement.

La cible est un **fournisseur d'identité standard (Keycloak, OpenID Connect, #690)**, qui lève ces limites. Le rattachement compte / organisme posé ici (`usershub_id_role`, uuid d'organisme) sera réutilisé : seul le moyen de vérifier l'identité changera. Il suffira d'ajouter un mode `AUTH_PROVIDER=oidc`.

## Mise en place sur l'instance RNF

Avant d'activer la connexion, réaligner les 4 organismes créés à la main dans CICADA qui doublonnent un organisme UsersHub : `scripts/rnf/2026-10-realignement-uuid-organismes.sql` (hors dépôt ; une seule fois). C'est un bloc `DO` unique, utilisable depuis DBeaver comme depuis psql : lancé tel quel (`appliquer := false`), il affiche le rapport avant/après puis s'interrompt sur « SIMULATION terminée » sans rien écrire ; passer `appliquer := true` après relecture. Sans ce réalignement, la première connexion d'un agent RNF créerait un second « Réserves Naturelles de France » et lui ferait perdre l'accès aux plans de son organisme.

**En service depuis le 15/10/2026** (réalignement appliqué le 14/10) :

| Réglage | Valeur |
|---|---|
| `GEONATURE_AUTH_URL` | `https://geonature.reserves-naturelles.org/api` (GeoNature 2.17.5) |
| `GEONATURE_AUTH_ID_APPLICATION` | `18` |
| `GEONATURE_AUTH_LIBELLE` | `RNF` |

`API_ENDPOINT` et la version se lisent sans authentification : `curl -s <URL_APPLICATION>/api/gn_commons/config` (clés `API_ENDPOINT`, `GEONATURE_VERSION`). Vérifier aussi que **le serveur CICADA** joint cette adresse (`curl -o /dev/null -w '%{http_code}' <API>/gn_commons/config` → 200) : si GeoNature partage l'IP publique de l'instance et que le pare-feu ne fait pas de *NAT reflection*, il faut une résolution interne du nom (cf. [Hub d'exploration fédérée](hub.md), « DNS interne »).

## Code

- `backend/apps/authentication/providers/usershub.py` — appels GeoNature, rattachement compte / organisme
- `POST /api/auth/login-geonature/`, `GET /api/auth/mode/` — `apps/authentication/views.py` ; fermeture des routes locales : `ConnexionLocaleActive` (`providers/__init__.py`) ; vérification au démarrage : `apps/authentication/checks.py`
- `Role.usershub_id_role` — migration `users/0012`
- Frontend : `features/auth/login.component.*`, `AuthService.login(…, mode)` / `getLoginMode()`, `connexionLocaleGuard` (inscription, mot de passe oublié)
- Tests : `backend/tests/integration/test_api_connexion_geonature.py`, `login.component.spec.ts`
