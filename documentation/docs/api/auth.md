# Authentification — référence

Connexion, rafraîchissement, inscription, mot de passe et impersonation. Les règles d'usage sont décrites dans [Authentification et permissions](authentification.md) ; un exemple complet dans [Prise en main](prise-en-main.md).

| Endpoint | Accès | Rôle |
|----------|-------|------|
| `POST /api/auth/login/` | public | Jetons JWT à partir d'un identifiant ou e-mail et d'un mot de passe |
| `POST /api/auth/login-geonature/` | public | Idem avec un compte GeoNature / UsersHub, si l'instance est en mode GeoNature |
| `GET /api/auth/mode/` | public | `cicada` ou `geonature` : le seul mode de connexion de l'instance |
| `POST /api/auth/refresh/` | public | Nouveau jeton d'accès (le compte doit toujours être actif) |
| `POST /api/auth/logout/` | authentifié | Révoque le jeton de rafraîchissement |
| `GET /api/auth/me/` | authentifié | Profil de l'utilisateur connecté |
| `POST /api/auth/register/` | public | Demande d'inscription (organisme existant ou à créer) |
| `GET /api/auth/registration-status/` | public | Statut d'une inscription par e-mail |
| `POST /api/auth/password-reset/`, `…/confirm/` | public | Réinitialisation du mot de passe |
| `GET /api/auth/stats/` | public | Statistiques générales affichées sur l'accueil |
| `GET /api/auth/health/` | public | Disponibilité du service d'authentification |
| `POST /api/auth/impersonate/{user_id}/` | super administrateur | Jetons de visualisation « en tant que » (lecture seule) |
| `POST /api/auth/stop-impersonation/` | super administrateur | Retour au compte d'origine |
| `GET /api/auth/impersonation-logs/` | super administrateur | Journal des sessions de visualisation |

## Référence interactive

<swagger-ui src="openapi/auth.json"/>
