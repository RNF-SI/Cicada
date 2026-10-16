# Authentification et permissions

## Jetons JWT

L'API utilise des jetons **JWT** (JSON Web Token). Un jeton d'accès accompagne chaque requête dans l'en-tête `Authorization`.

| Endpoint | Rôle |
|----------|------|
| `POST /api/auth/login/` | Connexion par identifiant (ou e-mail) et mot de passe → jeton d'accès + jeton de rafraîchissement |
| `POST /api/auth/refresh/` | Nouveau jeton d'accès à partir du jeton de rafraîchissement |
| `POST /api/auth/logout/` | Déconnexion (le jeton de rafraîchissement est révoqué) |
| `GET /api/auth/me/` | Informations sur l'utilisateur connecté |
| `POST /api/auth/register/` | Inscription publique (soumise à validation par un administrateur) |
| `GET /api/auth/registration-status/` | État d'une demande d'inscription |
| `GET /api/auth/health/` | Vérification publique de disponibilité |

### Exemple

```bash
# Connexion
curl -X POST https://<instance>/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "utilisateur@exemple.fr", "password": "…"}'
```

```bash
# Requête authentifiée
curl https://<instance>/api/auth/me/ \
  -H "Authorization: Bearer <jeton d'accès>"
```

Le jeton d'accès a une durée de vie limitée ; au-delà, l'API répond `401` et le client doit appeler `/api/auth/refresh/` avec le jeton de rafraîchissement.

!!! warning "Instances connectées à GeoNature"

    Une instance n'a qu'un seul mode de connexion : comptes CICADA **ou** comptes GeoNature, jamais les deux. Sur une instance GeoNature, la connexion passe par `/api/auth/login/` de la même façon, les identifiants étant vérifiés auprès de GeoNature.

## Rôles et niveaux d'accès

Les droits de l'API sont ceux de l'application. Ils se cumulent, du plus large au plus restreint :

| Rôle | Périmètre |
|------|-----------|
| **Super administrateur** | Toute l'instance : utilisateurs, organismes, sites, plans, paramètres |
| **Rédacteur général** | Lecture et écriture sur tous les plans, sites et organismes ; pas d'accès aux pages réservées au super administrateur |
| **Administrateur d'organisme** | Utilisateurs et sites de son organisme ; cycle de vie et exports des plans de son organisme |
| **Référent d'un plan** | Saisie, cycle de vie, suivi et exports du plan dont il est référent |
| **Rédacteur externe** | Saisie d'un plan sur lequel l'accès lui a été accordé ; jamais les suivis |
| **Utilisateur** | Lecture des sites et plans auxquels il est rattaché ; exploration des plans validés |

Règles transverses :

- **Verrouillage hors brouillon** : toute écriture sur un plan dont le statut n'est pas `draft` (ou sur l'un de ses éléments : enjeux, objectifs, indicateurs, actions, suivis, fichiers) est refusée avec `403`, quel que soit le rôle. Seules les actions de cycle de vie restent possibles.
- **Lecture seule élargie** : un utilisateur lié à un plan sans en être référent consulte toute son arborescence en lecture seule.
- **Exports** : réservés aux référents du plan et aux gestionnaires (administrateur d'organisme, rédacteur général, super administrateur).
- **Exploration** : un plan validé est consultable par tout utilisateur connecté depuis l'exploration des données, sans les données sensibles (budget, ressources humaines, mesures, réalisations, fichiers, personnes).

## Codes de réponse

| Code | Signification |
|------|---------------|
| `200` / `201` / `204` | Succès (lecture, création, suppression) |
| `400` | Requête invalide : le corps détaille les erreurs par champ |
| `401` | Jeton absent, invalide ou expiré |
| `403` | Droits insuffisants, ou plan verrouillé (hors brouillon) |
| `404` | Ressource inexistante ou hors du périmètre de l'utilisateur |
| `502` | Exploration nationale : hub injoignable (aucun repli sur l'index local) |
