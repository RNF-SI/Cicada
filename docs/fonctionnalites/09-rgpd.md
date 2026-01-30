# RGPD - Suppression de compte

### Comment ca marche

Cette fonctionnalite permet aux utilisateurs d'exercer leur droit a l'effacement conformement au RGPD (Reglement General sur la Protection des Donnees). L'utilisateur peut demander la suppression de son compte depuis son profil. La demande est ensuite traitee manuellement par un super administrateur.

### Le concept central

Le processus de suppression est **manuel** et gere par les super administrateurs :

```
Demande de suppression → Compte reste actif
                        → Notification aux admins
                        → Super admin traite la demande :
                          • Desactiver le compte
                          • Anonymiser les donnees
                          • Rejeter la demande
```

Ce systeme permet :
- Un controle total par les administrateurs sur le traitement des demandes
- La possibilite de verifier les implications avant toute action
- Une flexibilite dans le traitement (desactivation simple vs anonymisation complete)
- La communication avec l'utilisateur si necessaire

### Flux de suppression

#### 1. L'utilisateur fait sa demande

Depuis la page "Mon profil" (`/profile`), l'utilisateur voit une section "Mes donnees personnelles (RGPD)" avec :
- Une explication de ce que la suppression implique
- Un bouton "Supprimer mon compte"

En cliquant sur ce bouton, un dialogue de confirmation s'ouvre avec :
- Un avertissement clair sur les consequences
- La liste des effets de la suppression
- Un champ de confirmation ou l'utilisateur doit saisir son email

#### 2. Traitement de la demande

Quand l'utilisateur confirme :

| Action | Effet |
|--------|-------|
| `deletion_requested_at` | Enregistre la date/heure de la demande |
| `active` | **Reste True** (le compte reste actif) |
| Notifications | Envoyees aux personnes concernees (voir ci-dessous) |

L'utilisateur voit un message confirmant que sa demande a ete enregistree et sera traitee par un administrateur.

#### Notifications envoyees

Lors d'une demande de suppression, le systeme notifie automatiquement toutes les personnes concernees :

| Destinataire | Condition |
|--------------|-----------|
| **Super admins** | Tous les super admins actifs |
| **Admin de l'organisme** | Admin(s) de l'organisme de l'utilisateur |
| **Referents des sites** | Referents des sites ou l'utilisateur est membre |
| **Referents des plans** | Autres referents des plans ou l'utilisateur est referent |

> **Note** : Le systeme evite les doublons. Si une personne cumule plusieurs roles, elle ne recoit qu'une seule notification.

#### 3. Traitement par le super admin

Les super admins accedent a la page `/administration/rgpd` pour voir et traiter les demandes en cours.

**Actions disponibles :**

| Action | Effet | Reversible |
|--------|-------|------------|
| **Desactiver** | Desactive le compte (`active=False`), efface la demande | Oui |
| **Anonymiser** | Anonymise les donnees personnelles, desactive le compte | Non |
| **Rejeter** | Efface la demande, notifie l'utilisateur | Oui |

**Desactivation :**
- Le compte est desactive, l'utilisateur ne peut plus se connecter
- Les donnees personnelles sont conservees
- Le compte peut etre reactive par un admin si necessaire

**Anonymisation :**
| Champ | Avant | Apres |
|-------|-------|-------|
| `email` | `jean.dupont@example.fr` | `anonymized_12345@deleted.local` |
| `nom_role` | `Dupont` | `Utilisateur` |
| `prenom_role` | `Jean` | `Anonymise` |
| `is_anonymized` | `False` | `True` |
| `anonymized_at` | `null` | Date d'anonymisation |

**Rejet :**
- La demande est effacee
- L'utilisateur est notifie que sa demande a ete rejetee
- Le compte reste actif et fonctionnel

#### 4. Annulation par l'utilisateur

Tant que la demande n'a pas ete traitee, l'utilisateur peut l'annuler :

1. Se connecter avec ses identifiants
2. Sur son profil, un bandeau indique la demande en cours
3. Un bouton "Annuler la suppression" permet d'annuler

### Interface utilisateur

#### Page profil - Section RGPD

```
┌─────────────────────────────────────────────────────────┐
│  Mes donnees personnelles (RGPD)                        │
├─────────────────────────────────────────────────────────┤
│  Conformement au RGPD, vous pouvez demander la          │
│  suppression de votre compte et de vos donnees          │
│  personnelles.                                          │
│                                                         │
│  [ Supprimer mon compte ]                               │
└─────────────────────────────────────────────────────────┘
```

#### Etat "Suppression en attente"

Quand une demande est active, la section affiche :

```
┌─────────────────────────────────────────────────────────┐
│  Demande de suppression en cours                        │
├─────────────────────────────────────────────────────────┤
│  Votre demande de suppression a ete enregistree le      │
│  15/01/2026.                                            │
│                                                         │
│  Un administrateur traitera votre demande dans les      │
│  meilleurs delais.                                      │
│                                                         │
│  [ Annuler la suppression ]                             │
└─────────────────────────────────────────────────────────┘
```

#### Page administration RGPD (super_admin)

Accessible via `/administration/rgpd` pour les super administrateurs uniquement.

```
┌─────────────────────────────────────────────────────────┐
│  Demandes RGPD                                          │
│  Traitez les demandes de suppression de compte          │
├─────────────────────────────────────────────────────────┤
│  Utilisateur  │ Email        │ Date     │ Actions       │
│  ─────────────│──────────────│──────────│───────────────│
│  Jean Dupont  │ jean@ex.fr   │ 15/01/26 │ [Des] [Ano] [Rej] │
│  Marie Martin │ marie@ex.fr  │ 12/01/26 │ [Des] [Ano] [Rej] │
└─────────────────────────────────────────────────────────┘
```

### Securite

#### Confirmation par email

L'utilisateur doit saisir son email exact pour confirmer la suppression. Cette verification :
- Empeche les suppressions accidentelles (mauvais clic)
- Confirme que l'utilisateur comprend ce qu'il fait
- Est insensible a la casse

### Keycloak

Lorsque l'application est configuree avec `AUTH_PROVIDER=keycloak`, la gestion des comptes est deleguee a Keycloak :

- La page administration RGPD affiche un message d'avertissement
- Les boutons d'action sont desactives
- Les admins doivent traiter les demandes directement dans la console Keycloak

### Backend

#### Endpoints API

| Endpoint | Methode | Description | Acces |
|----------|---------|-------------|-------|
| `/api/users/users/request_deletion/` | POST | Demande de suppression | Utilisateur connecte |
| `/api/users/users/cancel_deletion/` | POST | Annulation de la demande | Utilisateur connecte |
| `/api/users/users/rgpd_requests/` | GET | Liste des demandes | super_admin |
| `/api/users/users/{id}/deactivate_rgpd/` | POST | Desactiver un compte | super_admin |
| `/api/users/users/{id}/anonymize_rgpd/` | POST | Anonymiser un compte | super_admin |
| `/api/users/users/{id}/reject_rgpd/` | POST | Rejeter une demande | super_admin |
| `/api/users/users/auth_provider/` | GET | Provider d'auth configure | Tous |

#### Reponses API

**Demande de suppression reussie :**
```json
{
  "status": "requested",
  "message": "Votre demande de suppression a ete enregistree. Un administrateur traitera votre demande dans les meilleurs delais."
}
```

**Annulation reussie :**
```json
{
  "status": "cancelled",
  "message": "Votre demande de suppression a ete annulee."
}
```

**Desactivation par admin :**
```json
{
  "status": "deactivated",
  "message": "Le compte de Jean Dupont a ete desactive."
}
```

**Anonymisation par admin :**
```json
{
  "status": "anonymized",
  "message": "Le compte a ete anonymise."
}
```

#### Modele User (champs RGPD)

| Champ | Type | Description |
|-------|------|-------------|
| `deletion_requested_at` | DateTimeField | Date de la demande de suppression |
| `is_anonymized` | BooleanField | Compte anonymise (defaut: False) |
| `anonymized_at` | DateTimeField | Date d'anonymisation |

#### Variable d'environnement

| Variable | Valeurs | Description |
|----------|---------|-------------|
| `AUTH_PROVIDER` | `local` (defaut), `keycloak` | Provider d'authentification |

### Integrite des donnees

L'anonymisation **preserve l'integrite referentielle** :

| Type de relation | Comportement |
|------------------|--------------|
| Plans de gestion | L'utilisateur reste dans les referents (anonymise) |
| Validations | L'historique des validations est conserve |
| Sites | Les associations utilisateur-site sont conservees |
| Notifications | Les notifications envoyees sont conservees |

Cela permet de maintenir l'historique et la tracabilite tout en respectant le droit a l'effacement.

### Traductions

Les cles de traduction sont dans `frontend/src/assets/i18n/fr.json` :

**Section profil (`profile.rgpd.*`) :**
| Cle | Texte |
|-----|-------|
| `profile.rgpd.title` | "Gestion de mon compte" |
| `profile.rgpd.deleteAccount` | "Supprimer mon compte" |
| `profile.rgpd.dialog.title` | "Supprimer mon compte" |
| `profile.rgpd.pendingDeletion.title` | "Suppression en cours" |

**Section admin (`admin.rgpd.*`) :**
| Cle | Texte |
|-----|-------|
| `admin.rgpd.title` | "Demandes RGPD" |
| `admin.rgpd.actions.deactivate` | "Desactiver" |
| `admin.rgpd.actions.anonymize` | "Anonymiser" |
| `admin.rgpd.actions.reject` | "Rejeter" |

### Tests

Les tests RGPD sont dans `tests/integration/test_api_users.py` :

| Classe | Tests |
|--------|-------|
| `TestUsersRGPDDeletion` | Demande de suppression, annulation, gestion des erreurs |
| `TestUsersRGPDModelMethods` | Methodes `request_deletion()`, `anonymize()`, `can_be_anonymized()` |
| `TestUsersRGPDNotifications` | Notifications aux super admins, admin_og, referents |
| `TestUsersRGPDAdminEndpoints` | Liste des demandes, desactivation, anonymisation, rejet |

Lancer les tests RGPD :
```bash
docker compose exec web pytest tests/integration/test_api_users.py -k RGPD -v
```

---

← [Pages d'administration](08-administration.md) | [Index](../FONCTIONNALITES.md) | [Tests](10-tests.md) →
