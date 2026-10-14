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

## ⚠️ Qui peut se connecter

GeoNature 2.17 (pypnusershub 3.x) **ne vérifie pas** les droits de la personne sur l'application dont l'`id_application` est transmis : il vérifie seulement que cette application existe, et que la personne a des droits sur **GeoNature lui-même** (`CODE_APPLICATION`, `pypnusershub/auth/providers/default.py`). Tout compte qui peut se connecter à GeoNature peut donc se connecter à CICADA.

## ⚠️ Limites — solution transitoire, cible : Keycloak (#690)

Cicada ne peut pas utiliser pypnusershub directement : c'est une bibliothèque **Flask**, liée à l'application GeoNature, inutilisable dans Django. Cicada passe donc par les **requêtes HTTP de l'API GeoNature**, ce qui a un coût :

- **Dépendance à la disponibilité de GeoNature** : GeoNature arrêté ou en maintenance = plus personne ne se connecte à Cicada (le mode est exclusif).
- **Dépendance à la version et au format de l'API** : routes `/auth/login` et `/users/organism/<id>`, forme de la réponse, comportement en cas de refus (redirection 302 sans `Accept: application/json`). Rien de cela n'est un contrat public : une mise à jour de GeoNature peut casser la connexion. À revérifier à chaque montée de version de GeoNature (essai contre la préprod).
- **Pas de contrôle d'accès par application** (voir plus haut) : tout compte GeoNature entre.
- **Le mot de passe transite par le serveur Cicada** : la personne le saisit dans Cicada, qui le relaie. Avec Keycloak (OpenID Connect), elle le saisit sur la page du fournisseur d'identité et Cicada ne le voit jamais.
- **Pas de session partagée** : se connecter à GeoNature ne connecte pas à Cicada, et inversement.

La cible est un **fournisseur d'identité standard (Keycloak, OpenID Connect, #690)**, qui lève ces limites. Le rattachement compte / organisme posé ici (`usershub_id_role`, uuid d'organisme) sera réutilisé : seul le moyen de vérifier l'identité changera. Il suffira d'ajouter un mode `AUTH_PROVIDER=oidc`.

## Mise en place sur l'instance RNF

Avant d'activer la connexion, réaligner les 4 organismes créés à la main dans CICADA qui doublonnent un organisme UsersHub : `scripts/rnf/2026-10-realignement-uuid-organismes.sql` (une seule fois ; rapport avant/après, se termine par `ROLLBACK` tant qu'on n'a pas relu). Sans ce réalignement, la première connexion d'un agent RNF créerait un second « Réserves Naturelles de France » et lui ferait perdre l'accès aux plans de son organisme.

## Code

- `backend/apps/authentication/providers/usershub.py` — appels GeoNature, rattachement compte / organisme
- `POST /api/auth/login-geonature/`, `GET /api/auth/mode/` — `apps/authentication/views.py` ; fermeture des routes locales : `ConnexionLocaleActive` (`providers/__init__.py`) ; vérification au démarrage : `apps/authentication/checks.py`
- `Role.usershub_id_role` — migration `users/0012`
- Frontend : `features/auth/login.component.*`, `AuthService.login(…, mode)` / `getLoginMode()`, `connexionLocaleGuard` (inscription, mot de passe oublié)
- Tests : `backend/tests/integration/test_api_connexion_geonature.py`, `login.component.spec.ts`
