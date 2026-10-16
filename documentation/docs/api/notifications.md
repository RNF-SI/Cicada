# Notifications, validations et activité

Trois mécanismes complémentaires : les **demandes de validation** (workflow), les **notifications** (ce qui concerne l'utilisateur) et l'**historique d'activité** (fil chronologique unifié). S'y ajoute l'accès aux **modules** de l'application.

## Demandes de validation

| Endpoint | Rôle |
|----------|------|
| `GET /api/validations/` | Demandes visibles par l'appelant (filtres : statut, type) |
| `GET /api/validations/my_requests/`, `…/pending_count/`, `…/types/` | Ses propres demandes ; compteur à traiter ; types et statuts disponibles |
| `GET /api/validations/{id}/`, `…/validators/` | Détail ; qui peut traiter la demande |
| `POST /api/validations/{id}/approve/`, `…/reject/`, `…/cancel/` | Approuver (commentaire facultatif), rejeter (commentaire obligatoire), annuler (demandeur) |
| `POST /api/validations/request_plan_access/`, `…/request_plan_site_link/` | Demander l'accès à un plan (éventuellement comme référent) ; demander de lier un site à un plan |
| `POST /api/validations/request_module_access/`, `…/grant_module_access/`, `…/revoke_module_access/`, `GET …/my_module_access/` | Accès aux modules |
| `POST /api/validations/request_admin_promotion/`, `…/request_admin_demotion/`, `…/request_admin_deactivation/` | Demandes d'un administrateur d'organisme vers le super administrateur |

Types de demandes : `user_registration`, `site_access`, `plan_access`, `referent_validation`, `plan_site_link`, `module_access`, créations de site et d'organisme, rattachements… Statuts : `pending` → `approved` / `rejected` / `cancelled` / `expired`.

**Lien plan–site** : le lien est direct (sans demande) pour le super administrateur, et pour un référent du plan qui est aussi référent du site ou administrateur de son organisme. Sinon la demande est adressée aux référents du site (si le demandeur est référent du plan) ou aux référents du plan.

## Notifications

| Endpoint | Rôle |
|----------|------|
| `GET /api/notifications/`, `…/unread/`, `…/count/` | Notifications de l'appelant, non lues, compteur |
| `POST /api/notifications/{id}/mark_read/`, `…/mark_all_read/` | Marquer comme lu |
| `GET /api/notifications/poll/?since=<horodatage>` | Nouveautés depuis un instant (utilisé par la cloche de l'en-tête) |

Types : `welcome`, `validation_request`, `validation_approved`, `validation_rejected`, `user_associated_site`, `user_associated_plan`, `user_removed_site`, `user_removed_plan`, `account_deactivated`, `account_activated`, `organisme_changed`, `site_orphaned`, `organisme_no_admin`, `plan_csrpn_transition`, `system_alert`, `info`.

## Historique d'activité

| Endpoint | Rôle |
|----------|------|
| `GET /api/activity/` | Fil chronologique, filtré selon le rôle (`entity_type`, `action`, `site_id`, `plan_id`, `since`, `search`) |
| `GET /api/activity/my_sites/`, `…/my_plans/`, `…/my_rights/`, `…/validations/`, `…/rgpd/`, `…/system/` | Les onglets de la page Activité ; `rgpd` et `system` sont réservés au super administrateur |
| `GET /api/activity/stats/`, `…/tabs_counts/` | Statistiques et compteurs par onglet |

Entités : `site`, `plan`, `user`, `organisme`, `validation`. Actions : `create`, `update`, `delete`, `add_member`, `remove_member`, `add_referent`, `remove_referent`, `status_change`, `activate`, `deactivate`, `rgpd_request`, `rgpd_anonymized`…

## Modules

`GET /api/modules/my_accessible/` liste les modules ouverts à l'appelant, `…/requiring_access/` ceux qui demandent une autorisation, `…/{id}/access_status/` l'état d'une demande. Le super administrateur gère les modules (`/api/modules/`, `…/all/`).

## Référence interactive

<swagger-ui src="openapi/notifications.json"/>
