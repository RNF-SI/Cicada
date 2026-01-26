# Historique d'activité

### Comment ça marche

L'historique d'activité fournit une timeline unifiée de tout ce qui se passe sur les sites, plans et utilisateurs. Contrairement aux notifications (qui sont destinées à informer un utilisateur spécifique), l'historique d'activité trace l'ensemble des actions sur les entités.

### Différence avec les notifications

| Aspect | Notification | ActivityLog |
|--------|--------------|-------------|
| **Focus** | Utilisateur (destinataire) | Entité (site, plan, user) |
| **Durée** | Temporaire (expire, supprimable) | Permanent (audit) |
| **Contenu** | Message simple | Détails des changements |
| **Accès** | Pull par utilisateur | Query par entité/rôle |

### Ce qui est tracé

Le système enregistre automatiquement les activités suivantes :

| Type d'entité | Actions tracées |
|---------------|-----------------|
| **Site** | Création, modification, suppression |
| **Plan de gestion** | Création, modification, suppression, changement de statut |
| **Utilisateur** | Activation, désactivation, changements de rôle |
| **Membre site** | Ajout, retrait, nomination référent |
| **Référent plan** | Ajout, retrait |
| **Validation** | Approbation, rejet |
| **RGPD** | Demande de suppression, annulation, anonymisation |

### Signaux automatiques

Les activités sont enregistrées automatiquement via les signaux Django (`apps/core/activity_signals.py`). Quand un site est modifié, un plan créé, ou un utilisateur ajouté à un site, le système enregistre l'événement sans intervention du code métier.

### Visibilité par rôle

L'API filtre les activités visibles selon le rôle de l'utilisateur :

| Rôle | Ce qu'il voit |
|------|---------------|
| **Super admin** | Tout, y compris RGPD et alertes système |
| **Admin organisme** | Activités de son organisme et des sites gérés |
| **Référent** | Activités de ses sites et plans |
| **Utilisateur** | Activités des sites où il est membre |

### Frontend : Page `/activite`

La page d'activité présente une timeline avec des onglets dynamiques selon le rôle :
- **Tous** : Tout, Mes sites, Mes plans, Mes droits, Notifications
- **Admin** : + Validations
- **Super admin** : + RGPD, Système

#### Onglet "Mes droits"

L'onglet **Mes droits** permet à chaque utilisateur de consulter l'historique des changements concernant ses propres droits et permissions :
- Ajout/retrait comme membre d'un site
- Nomination/retrait comme référent (site ou plan)
- Activation/désactivation du compte
- Validation ou rejet de demandes d'accès

Les activités sont groupées chronologiquement (Aujourd'hui, Hier, Cette semaine, Ce mois, Plus ancien) avec des icônes et couleurs selon le type d'action.

### Documentation technique

Voir le guide complet : [docs/API_ACTIVITY_GUIDE.md](API_ACTIVITY_GUIDE.md)

---

---

← [Validations](03-validations.md) | [Index](../FONCTIONNALITES.md) | [Impersonnation](05-impersonnation.md) →
