# Utilisateurs

Comptes, rôles et droits. Un utilisateur appartient à un organisme, porte un rôle (`niveau_role`) et des rattachements à des sites (membre ou référent) et à des plans (membre ou référent).

| Endpoint | Rôle |
|----------|------|
| `GET/POST /api/users/users/` | Liste (scopée au périmètre de l'appelant) et création de comptes |
| `GET/PUT/PATCH/DELETE /api/users/users/{id}/` | Détail et modification d'un compte |
| `GET /api/users/users/me/`, `POST …/set_identifiant/` | Son propre compte ; définir son identifiant de connexion s'il est vide |
| `POST /api/users/users/{id}/assign_site/`, `DELETE …/sites/{site_id}/` | Rattacher ou détacher un site (membre ou référent) |
| `POST /api/users/users/{id}/set-redacteur-principal/`, `…/remove-redacteur-principal/` | Attribuer ou retirer le rôle de rédacteur général (super administrateur) |
| `POST /api/users/users/{id}/set-redacteur/`, `…/remove-redacteur/` | Attribuer ou retirer le rôle de rédacteur externe (super administrateur) |
| `POST /api/users/users/{id}/change_password/` | Changer un mot de passe |
| `POST /api/users/users/request_deletion/`, `…/cancel_deletion/` | Demande de suppression de son compte (RGPD) et annulation |
| `GET /api/users/users/rgpd_requests/`, `POST …/{id}/deactivate_rgpd/`, `…/anonymize_rgpd/`, `…/reject_rgpd/` | Traitement des demandes RGPD (super administrateur) |
| `GET /api/users/users/stats/`, `GET /api/users/users/auth_provider/` | Statistiques ; fournisseur d'authentification configuré |
| `GET /api/users/permissions/` | Diagnostic des droits de l'appelant |

## Règles

- **Périmètre** : un super administrateur et un rédacteur général voient tous les comptes ; un administrateur d'organisme ceux de son organisme ; un utilisateur ne voit que lui-même.
- **Activation et désactivation** d'un compte : super administrateur uniquement (un motif est demandé à la désactivation). Un administrateur d'organisme passe par une [demande de validation](notifications.md) pour promouvoir ou rétrograder un administrateur.
- **Rôles attribués par l'API** : `set-redacteur-principal` et `set-redacteur` sont réservés au super administrateur ; la réponse renvoie le compte mis à jour.
- Les modifications de rattachement déclenchent des **notifications** (`user_associated_site`, `user_removed_site`…) et une entrée dans l'[historique d'activité](notifications.md).

## Référence interactive

<swagger-ui src="openapi/users.json"/>
