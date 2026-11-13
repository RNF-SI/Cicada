# Impersonnation

### Comment ça marche

L'impersonnation permet à un super admin de "devenir" temporairement un autre utilisateur pour voir l'application comme lui, diagnostiquer des problèmes ou vérifier des permissions.

### Le flux complet

#### Démarrage

1. Le super admin va dans la liste des utilisateurs et clique "Impersonner" sur un utilisateur
2. Les jetons du super admin sont **révoqués** au départ : le navigateur ne les garde pas (`POST /api/auth/impersonate/<id>/`)
3. Une requête est envoyée au backend avec l'ID de l'utilisateur cible
4. Le backend vérifie :
   - Est-ce un super admin ?
   - Ne s'impersonne-t-il pas lui-même ?
   - La cible n'est-elle pas un super admin ?
5. Un log d'audit est créé avec : qui impersonne qui, IP, navigateur, heure de début
6. De nouveaux tokens JWT sont générés pour l'utilisateur cible, mais avec des informations supplémentaires cachées dans le token : "ceci est une session d'impersonnation, l'admin original est X"
7. Le frontend remplace ses tokens par les nouveaux
8. L'admin voit maintenant l'application comme l'utilisateur cible

#### Pendant l'impersonnation

- L'interface affiche une bannière "Vous impersonnez [Nom]"
- Toutes les requêtes API utilisent le token de l'utilisateur impersonné
- L'utilisateur impersonné ne sait pas qu'il est impersonné

#### Arrêt

1. L'admin clique sur "Arrêter l'impersonnation" (`POST /api/auth/stop-impersonation/`), ou se déconnecte
2. Le backend lit l'auteur dans le jeton (`impersonator_id`, `impersonation_log_id`)
3. Le log d'audit (`ImpersonationLog`) reçoit l'heure de fin
4. De nouveaux jetons sont émis pour l'admin, qui retrouve son contexte
5. Le jeton d'impersonation est refusé dès la requête suivante

### Sécurité

| Règle | Description |
|-------|-------------|
| Accès restreint | Seuls les super admins peuvent impersonner |
| Protection super admins | Impossible d'impersonner un autre super admin (protection contre l'escalade) |
| Traçabilité complète | Tout est tracé : qui, qui, quand, combien de temps, depuis quelle IP |
| Durée limitée | **Une heure au plus** (`DUREE_IMPERSONATION`, `apps/authentication/sessions.py`) |
| Contrôle à chaque requête | Session arrêtée, expirée ou dont l'auteur n'est plus super admin actif → jeton refusé (`impersonation_refusee()`) |

### Mode lecture seule

Les modifications (POST, PUT, PATCH, DELETE) sont **refusées par le serveur** pendant l'impersonnation (`refuser_ecriture_en_impersonation()`, `apps/authentication/activite.py`) : un appel direct avec le jeton d'impersonation ne peut pas écrire au nom de la personne. Seuls `stop-impersonation`, `refresh` et `logout` restent permis. Cela permet de :
- Consulter l'application comme un utilisateur sans risque de modification
- Garantir la traçabilité : aucune action ne peut être effectuée au nom d'un autre
- Protéger les données en production

En **développement**, le réglage `IMPERSONATION_ECRITURE` (vrai par défaut dans `settings/development.py`, faux ailleurs) lève ce blocage pour faciliter les tests. L'interface applique la même règle pour prévenir l'utilisateur avant l'envoi.

#### Indicateurs visuels

Quand le mode lecture seule est actif, l'utilisateur voit clairement qu'il ne peut pas modifier :

| Élément | Mode normal | Mode lecture seule |
|---------|-------------|-------------------|
| **Couleur du bandeau** | Orange (warning) | Rouge (error) |
| **Badge** | Aucun | "Mode lecture seule" avec icône 🔒 |
| **Clic sur action** | Action exécutée | Message snackbar d'erreur |

#### Comportement technique

1. **Intercepteur HTTP** (`impersonation.interceptor.ts`) :
   - Intercepte toutes les requêtes sortantes
   - Bloque les méthodes POST, PUT, PATCH, DELETE si en mode lecture seule
   - Autorise toujours GET, HEAD, OPTIONS
   - Autorise certains endpoints critiques (stop-impersonation, refresh, logout)

2. **Service `ImpersonationGuardService`** :
   - Signal `isReadOnly` : true si impersonnation + modifications bloquées
   - Signal `canModify` : inverse pour faciliter les bindings
   - Méthode `checkCanModify()` : vérifie et affiche un message si bloqué

3. **Requêtes bloquées** :
   - Ne sont jamais envoyées au serveur
   - Retournent une erreur HTTP 403 locale
   - Affichent un snackbar explicatif à l'utilisateur

#### Configuration

| Mode | Fichier | `allowImpersonationModifications` | Comportement |
|------|---------|-----------------------------------|--------------|
| Développement | `environment.ts` | `true` | Modifications autorisées |
| Production | `environment.prod.ts` | `false` | Consultation uniquement |

#### Utilisation dans les composants

Pour désactiver visuellement un bouton en mode lecture seule :

```typescript
// Dans le composant
import { ImpersonationGuardService } from '@core/services/impersonation-guard.service';

readonly impersonationGuard = inject(ImpersonationGuardService);
readonly canModify = this.impersonationGuard.canModify;

// Vérification avant action
onSave() {
  if (!this.impersonationGuard.checkCanModify()) return;
  // ... continuer avec la sauvegarde
}
```

```html
<!-- Dans le template -->
<button [disabled]="!canModify()" (click)="onSave()">Enregistrer</button>
```

#### Modifications en production

Il n'y en a pas : le serveur refuse les écritures quelle que soit la configuration de l'interface. Pour corriger quelque chose, utilisez votre propre compte d'administrateur ou demandez à l'utilisateur de le faire.

---

---

← [Historique d'activité](04-activite.md) | [Index](../FONCTIONNALITES.md) | [Modules](06-modules.md) →
