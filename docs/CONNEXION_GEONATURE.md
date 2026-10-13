# Connexion par un GeoNature / UsersHub

Issues : #689 (connexion), #691 (organismes).

Une instance CICADA peut accepter, **en plus** de ses comptes propres, les comptes d'un GeoNature / UsersHub — c'est le cas de l'instance RNF. Désactivée par défaut : une instance installée sans réglage n'appelle jamais GeoNature.

## Prérequis

- **GeoNature 2.17.0 ou plus récent.** Cette version ajoute `GET <API>/users/organism/<id>` (fiche d'un organisme) et impose `pypnusershub >= 3.2.0`, qui accepte le jeton en `Authorization: Bearer`. Avec une version plus ancienne, la connexion fonctionne mais le compte n'est **pas** rattaché à son organisme.
- Une application CICADA déclarée dans UsersHub (son `id_application`).

## Réglages

Proposés par l'installeur (« Connexion par un GeoNature »), écrits dans `/var/lib/cicada/.env` :

| Variable | Rôle |
|---|---|
| `GEONATURE_AUTH_URL` | adresse de l'**API** GeoNature = la valeur `API_ENDPOINT` de sa configuration (ex. `https://geonature.exemple.fr/api` derrière Apache ; `http://127.0.0.1:5000` en développement). Vide = désactivée |
| `GEONATURE_AUTH_ID_APPLICATION` | `id_application` de CICADA dans UsersHub |
| `GEONATURE_AUTH_LIBELLE` | nom affiché : « RNF » → bouton « Compte RNF » |
| `GEONATURE_AUTH_ORGANISMES_EXCLUS` | `id_organisme` UsersHub qui ne sont pas de vrais organismes (« Autre », « ALL », tests), séparés par des virgules |
| `GEONATURE_AUTH_TIMEOUT` | délai des appels à GeoNature, en secondes (défaut 10) |

Après modification : `docker compose up -d web`.

## Déroulé d'une connexion

1. La page de connexion propose « Compte <libellé> » et « Compte CICADA ». Le mot de passe saisi part au **serveur** CICADA, qui le relaie à GeoNature (`POST <API>/auth/login`) ; le navigateur ne parle jamais à GeoNature, et le mot de passe n'est ni stocké ni journalisé.
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

- Un compte CICADA dont l'**email** est celui du compte UsersHub est relié à la première connexion : il garde son rôle, ses plans et son mot de passe CICADA (secours si GeoNature est en panne).
- Avec un email différent, un **second compte** serait créé. Consigne : créer le compte UsersHub avec l'email déjà utilisé dans CICADA.
- Les personnes sans compte UsersHub continuent avec « Compte CICADA ».

## Cas d'erreur

| Situation | Résultat |
|---|---|
| Identifiant ou mot de passe faux | refus (401) |
| GeoNature injoignable | refus (502) ; « Compte CICADA » reste utilisable |
| Compte UsersHub sans email | refus (403) |
| Compte CICADA désactivé ou en attente de validation | refus (403) |
| Email déjà porté par un compte relié à un autre compte UsersHub | refus (409), à régler par un administrateur |
| Organisme illisible (panne, GeoNature < 2.17) | connexion acceptée, organisme inchangé, erreur journalisée |
| Organisme exclu | connexion acceptée, sans organisme |

## ⚠️ Qui peut se connecter

GeoNature 2.17 (pypnusershub 3.x) **ne vérifie pas** les droits de la personne sur l'application dont l'`id_application` est transmis : il vérifie seulement que cette application existe, et que la personne a des droits sur **GeoNature lui-même** (`CODE_APPLICATION`, `pypnusershub/auth/providers/default.py`). Tout compte qui peut se connecter à GeoNature peut donc se connecter à CICADA.

## Mise en place sur l'instance RNF

Avant d'activer la connexion, réaligner les 4 organismes créés à la main dans CICADA qui doublonnent un organisme UsersHub : `scripts/rnf/2026-10-realignement-uuid-organismes.sql` (une seule fois ; rapport avant/après, se termine par `ROLLBACK` tant qu'on n'a pas relu). Sans ce réalignement, la première connexion d'un agent RNF créerait un second « Réserves Naturelles de France » et lui ferait perdre l'accès aux plans de son organisme.

## Code

- `backend/apps/authentication/providers/usershub.py` — appels GeoNature, rattachement compte / organisme
- `POST /api/auth/login-geonature/`, `GET /api/auth/modes/` — `apps/authentication/views.py`
- `Role.usershub_id_role` — migration `users/0012`
- Frontend : `features/auth/login.component.*`, `AuthService.login(…, mode)` / `getLoginModes()`
- Tests : `backend/tests/integration/test_api_connexion_geonature.py`, `login.component.spec.ts`
