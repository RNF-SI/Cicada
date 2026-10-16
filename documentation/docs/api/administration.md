# Administration de l'instance

Endpoints réservés au super administrateur (sauf mention), qui correspondent aux pages de l'espace d'administration décrites dans la [notice Administrateur d'une instance](../admin-instance/index.md).

| Endpoint | Rôle |
|----------|------|
| `GET /api/settings/` | Configuration de l'instance (**public** : image d'accueil, couleur du bandeau, logo, mode de connexion, options activées) |
| `PATCH /api/settings/` | Modification : apparence, couleur des exports, champ « ID Doc'Gestion FCEN », mesure d'audience Matomo, `api_publique_plans`, `federation_partage` (décocher retire immédiatement les plans du hub) |
| `GET /api/settings/homepage-image/`, `…/structure-logo/` | Image d'accueil et logo de la structure (binaires) |
| `GET /api/admin/orphans/`, `…/counts/` | Sites sans utilisateur et plans sans site (administrateur d'organisme et plus, scopé à l'organisme) |
| `GET /api/admin/error-logs/`, `…/{id}/`, `…/stats/`, `…/unacknowledged_count/` | Journal des erreurs applicatives |
| `POST /api/admin/error-logs/{id}/acknowledge/`, `…/acknowledge_all/` | Acquitter une erreur, ou toutes |
| `GET /api/admin/logs/?file=&level=` | Fichiers de journaux du serveur (général, erreurs, audit), filtrés par niveau, téléchargeables |
| `GET /api/system/version/`, `…/app-version/` | Version installée et dernière version disponible ; version courte pour l'affichage |
| `POST /api/system/trigger-update/` `{ "version": "0.1.56" }` | Déclenche la mise à jour de l'instance (paquet Debian) |

Les comptes, rôles et demandes RGPD sont dans [Utilisateurs](users.md) ; les validations dans [Notifications, validations et activité](notifications.md).

## Référence interactive

<swagger-ui src="openapi/administration.json"/>
