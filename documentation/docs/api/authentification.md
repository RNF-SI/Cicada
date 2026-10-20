# Authentification et permissions

## Jetons JWT

L'API utilise des jetons **JWT** (JSON Web Token) : un jeton d'accès à durée de vie courte, à transmettre dans l'en-tête `Authorization: Bearer <access>`, et un jeton de rafraîchissement à durée de vie longue, renouvelé à chaque utilisation et révoqué à la déconnexion.

| Endpoint | Rôle |
|----------|------|
| `POST /api/auth/login/` | Connexion par identifiant ou e-mail et mot de passe |
| `POST /api/auth/login-geonature/` | Connexion avec un compte GeoNature / UsersHub (instances reliées à GeoNature) |
| `GET /api/auth/mode/` | Mode de connexion de l'instance : comptes CICADA **ou** GeoNature, jamais les deux |
| `POST /api/auth/refresh/` | Nouveau jeton d'accès à partir du jeton de rafraîchissement |
| `POST /api/auth/logout/` | Déconnexion : le jeton de rafraîchissement est mis sur liste noire |
| `GET /api/auth/me/` | L'utilisateur connecté, son rôle et ses rattachements |
| `POST /api/auth/register/` | Inscription publique, soumise à validation par un administrateur |
| `GET /api/auth/registration-status/?email=` | État d'une demande d'inscription |
| `POST /api/auth/password-reset/` et `…/confirm/` | Réinitialisation du mot de passe par e-mail |
| `POST /api/auth/impersonate/{user_id}/` et `POST /api/auth/stop-impersonation/` | Mode visualisation du super administrateur (lecture seule, tracé dans `impersonation-logs`) |

Le détail (corps, réponses, codes) est dans la page [Authentification — référence](auth.md).

## Rôles et niveaux d'accès

Les droits de l'API sont ceux de l'application. Ils se cumulent, du plus large au plus restreint :

| Rôle (`niveau_role`) | Périmètre |
|------|-----------|
| **Super administrateur** (`super_admin`) | Toute l'instance : utilisateurs, organismes, sites, plans, paramètres, journaux |
| **Rédacteur général** (`redacteur_principal`) | Lecture et écriture sur tous les plans, sites et organismes ; pas d'accès aux pages réservées au super administrateur ; ne supprime pas de site |
| **Administrateur d'organisme** (`admin_og`) | Utilisateurs et sites de son organisme ; cycle de vie et exports des plans de son organisme |
| **Rédacteur externe** (`redacteur`) | Saisie des plans sur lesquels l'accès lui a été accordé ; jamais les suivis ; aucun plan par défaut |
| **Utilisateur** (`utilisateur`) | Lecture des sites et plans auxquels il est rattaché ; exploration des plans validés |

S'y ajoute un **niveau d'accès**, indépendant du rôle : être **référent** d'un site ou d'un plan donne la main sur cet objet (saisie, cycle de vie, suivi, exports du plan).

## Règles transverses

- **Verrouillage hors brouillon** : toute écriture sur un plan dont le statut n'est pas `draft`, ou sur l'un de ses éléments (enjeux, objectifs, indicateurs, actions, suivis, fichiers), est refusée avec `403`, quel que soit le rôle. Seules les actions de cycle de vie (`change-status`, `duplicate`, `create-evaluation`, `extend-duration`, `start-revision`…) et la gestion des sites, référents et membres restent possibles.
- **Lecture seule élargie** : un utilisateur lié à un plan sans en être référent (membre, rattaché à un site du plan, membre d'un organisme rédacteur ou gestionnaire) consulte toute son arborescence en lecture seule. Le membre du plan et l'utilisateur rattaché à l'un de ses sites consultent aussi ses suivis (bilan, réalisations) ; la saisie et les exports restent aux référents et gestionnaires.
- **Lecture d'exploration** : un plan validé est consultable par tout utilisateur connecté depuis l'exploration des données, sans ses données sensibles (budget, ressources humaines, mesures, réalisations, fichiers, personnes). Les réponses sont alors marquées `acces_exploration: true`.
- **Exports** : réservés aux référents du plan et aux gestionnaires (administrateur d'organisme, rédacteur général, super administrateur). Les classeurs **exemples** (`example-*-xlsx`) restent ouverts à tout utilisateur authentifié.
- **Périmètre invisible** : un objet hors périmètre renvoie `404`, pas `403`.
- **Impersonation** : pendant une session de visualisation, toute écriture est refusée.

## Vérifier ses droits

`GET /api/users/permissions/` renvoie le rôle effectif, les méthodes de permission évaluées pour l'utilisateur (`is_super_admin`, `is_redacteur_principal`, `is_referent`…) et ses rattachements. C'est l'endpoint à utiliser pour diagnostiquer un `403`.
