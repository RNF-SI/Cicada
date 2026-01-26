# RGPD - Suppression de compte

### Comment ça marche

Cette fonctionnalité permet aux utilisateurs d'exercer leur droit à l'effacement conformément au RGPD (Règlement Général sur la Protection des Données). L'utilisateur peut demander la suppression de son compte depuis son profil.

### Le concept central

Le processus de suppression comporte un **délai de grâce de 30 jours** :

```
Demande de suppression → Compte désactivé immédiatement
                        → Délai de 30 jours pour annuler
                        → Anonymisation définitive après 30 jours
```

Ce délai permet :
- À l'utilisateur de changer d'avis et récupérer son compte
- De prévenir les suppressions accidentelles
- De maintenir l'intégrité des données référentielles (plans, validations, etc.)

### Flux de suppression

#### 1. L'utilisateur fait sa demande

Depuis la page "Mon profil" (`/profile`), l'utilisateur voit une section "Mes données personnelles (RGPD)" avec :
- Une explication de ce que la suppression implique
- Un bouton "Supprimer mon compte"

En cliquant sur ce bouton, un dialogue de confirmation s'ouvre avec :
- Un avertissement clair sur l'irréversibilité
- La liste des conséquences (accès bloqué, données supprimées, etc.)
- L'information sur le délai de grâce de 30 jours
- Un champ de confirmation où l'utilisateur doit saisir son email

#### 2. Traitement de la demande

Quand l'utilisateur confirme :

| Action | Effet |
|--------|-------|
| `deletion_requested_at` | Enregistre la date/heure de la demande |
| `active = False` | Compte désactivé immédiatement |
| Token refresh | Bloqué - l'utilisateur est déconnecté |

L'utilisateur voit alors un message confirmant sa demande avec la date prévue de suppression définitive.

#### 3. Période de grâce (30 jours)

Pendant ces 30 jours, l'utilisateur peut **annuler sa demande** :

1. Se reconnecter avec ses identifiants habituels
2. Sur son profil, un bandeau d'avertissement orange indique la suppression en cours
3. Un bouton "Annuler la suppression" permet de restaurer le compte

Si l'utilisateur annule :
- `deletion_requested_at` est remis à `null`
- `active` est remis à `True`
- Le compte fonctionne à nouveau normalement

#### 4. Anonymisation (après 30 jours)

Une tâche Celery quotidienne (`process_deletion_requests`) vérifie les comptes à anonymiser :

1. Identifie les utilisateurs avec `deletion_requested_at` > 30 jours
2. Pour chaque compte éligible, anonymise les données :

| Champ | Avant | Après |
|-------|-------|-------|
| `email` | `jean.dupont@example.fr` | `anonymized_12345@deleted.local` |
| `nom_role` | `Dupont` | `Utilisateur` |
| `prenom_role` | `Jean` | `Anonymisé` |
| `is_anonymized` | `False` | `True` |
| `anonymized_at` | `null` | Date d'anonymisation |

3. Notifie les super admins du nombre de comptes anonymisés

### Interface utilisateur

#### Page profil - Section RGPD

```
┌─────────────────────────────────────────────────────────┐
│  Mes données personnelles (RGPD)                        │
├─────────────────────────────────────────────────────────┤
│  Conformément au RGPD, vous pouvez demander la          │
│  suppression de votre compte et de vos données          │
│  personnelles.                                          │
│                                                         │
│  [ Supprimer mon compte ]                               │
└─────────────────────────────────────────────────────────┘
```

#### État "Suppression en cours"

Quand une demande est active, la section affiche :

```
┌─────────────────────────────────────────────────────────┐
│  ⚠️ Suppression programmée                              │
├─────────────────────────────────────────────────────────┤
│  Votre demande de suppression a été enregistrée le      │
│  15/01/2026. Votre compte sera définitivement           │
│  supprimé le 14/02/2026 (dans 23 jours).                │
│                                                         │
│  Vous pouvez annuler cette demande à tout moment        │
│  avant cette date.                                      │
│                                                         │
│  [ Annuler la suppression ]                             │
└─────────────────────────────────────────────────────────┘
```

#### Dialogue de confirmation

Le dialogue de suppression affiche :

| Section | Contenu |
|---------|---------|
| **Titre** | "Supprimer mon compte" avec icône corbeille rouge |
| **Avertissement** | Bannière rouge "Cette action est irréversible" |
| **Conséquences** | Liste à puces des effets (accès bloqué, données supprimées, etc.) |
| **Délai de grâce** | Encart bleu expliquant les 30 jours de réflexion |
| **Confirmation** | Champ où l'utilisateur saisit son email pour confirmer |
| **Boutons** | "Annuler" et "Supprimer définitivement" |

### Sécurité

#### Blocage du token refresh

Quand un utilisateur demande la suppression de son compte, le système bloque le renouvellement des tokens JWT :

```python
# Dans CustomTokenRefreshView
if user.deletion_requested_at is not None:
    raise InvalidToken("Ce compte a demandé sa suppression")
```

Cela garantit que :
- L'utilisateur est déconnecté quand son access token expire (60 min)
- Il ne peut pas continuer à utiliser l'application
- Il peut toujours se reconnecter pour annuler sa demande

#### Confirmation par email

L'utilisateur doit saisir son email exact pour confirmer la suppression. Cette vérification :
- Empêche les suppressions accidentelles (mauvais clic)
- Confirme que l'utilisateur comprend ce qu'il fait
- Est insensible à la casse (comparaison en minuscules)

### Backend

#### Endpoints API

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/users/users/request_deletion/` | POST | Demande de suppression |
| `/api/users/users/cancel_deletion/` | POST | Annulation de la demande |

#### Réponses API

**Demande de suppression réussie :**
```json
{
  "status": "success",
  "message": "Votre demande de suppression a été enregistrée."
}
```

**Annulation réussie :**
```json
{
  "status": "success",
  "message": "Votre demande de suppression a été annulée."
}
```

#### Modèle User (champs RGPD)

| Champ | Type | Description |
|-------|------|-------------|
| `deletion_requested_at` | DateTimeField | Date de la demande de suppression |
| `is_anonymized` | BooleanField | Compte anonymisé (défaut: False) |
| `anonymized_at` | DateTimeField | Date d'anonymisation |

### Tâche Celery

La tâche `process_deletion_requests` s'exécute **tous les jours à 6h00** :

1. Recherche les comptes avec `deletion_requested_at` non null et `is_anonymized = False`
2. Vérifie que 30 jours se sont écoulés depuis la demande
3. Anonymise les données personnelles
4. Envoie une notification aux super admins avec le résumé

### Intégrité des données

L'anonymisation **préserve l'intégrité référentielle** :

| Type de relation | Comportement |
|------------------|--------------|
| Plans de gestion | L'utilisateur reste dans les référents (anonymisé) |
| Validations | L'historique des validations est conservé |
| Sites | Les associations utilisateur-site sont conservées |
| Notifications | Les notifications envoyées sont conservées |

Cela permet de maintenir l'historique et la traçabilité tout en respectant le droit à l'effacement.

### Traductions

Les clés de traduction sont dans `frontend/src/assets/i18n/fr.json` sous `profile.rgpd.*` :

| Clé | Texte |
|-----|-------|
| `profile.rgpd.title` | "Mes données personnelles (RGPD)" |
| `profile.rgpd.description` | "Conformément au RGPD, vous pouvez demander..." |
| `profile.rgpd.deleteButton` | "Supprimer mon compte" |
| `profile.rgpd.dialog.title` | "Supprimer mon compte" |
| `profile.rgpd.dialog.warning` | "Cette action est irréversible" |
| `profile.rgpd.pendingDeletion.title` | "Suppression programmée" |
| `profile.rgpd.cancelSuccess` | "Votre demande de suppression a été annulée" |

---

---

← [Pages d'administration](08-administration.md) | [Index](../FONCTIONNALITES.md) | [Tests](10-tests.md) →
