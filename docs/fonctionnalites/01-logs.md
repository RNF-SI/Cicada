# Système de Logs
# Système de Logs

### Comment ça marche

Le système de logs trace tout ce qui se passe dans l'application pour le debugging et l'audit.

### Principe du Correlation ID

Quand une requête HTTP arrive, le système génère un identifiant unique (UUID). Cet identifiant est attaché à **tous** les logs générés pendant le traitement de cette requête. Ainsi, si un bug survient, on peut filtrer les logs par cet ID et voir exactement tout ce qui s'est passé pour cette requête spécifique.

### Flux d'une requête

1. La requête arrive → le middleware génère un UUID (ex: `f4f5f562-5b94...`)
2. Ce UUID est stocké dans un espace mémoire temporaire (thread-local)
3. Chaque fois qu'un log est écrit quelque part dans le code, le système ajoute automatiquement cet UUID
4. La réponse part avec le même UUID dans un header HTTP
5. L'espace mémoire est nettoyé

### Les 3 types de logs

| Fichier | Contenu |
|---------|---------|
| `django.log` | Logs généraux - tout ce qui se passe (infos, warnings) |
| `error.log` | Erreurs uniquement - pour les identifier rapidement |
| `audit.log` | Qui a fait quoi ? Trace les actions de modification |

### L'audit

Quand un utilisateur fait un POST, PUT, PATCH ou DELETE sur certains endpoints (users, sites, plans, organismes), le middleware enregistre automatiquement :
- **Qui** : email, id de l'utilisateur
- **Quoi** : méthode HTTP, chemin de l'API
- **Quand** : timestamp
- **Résultat** : code HTTP de la réponse

---

← | [Index](../FONCTIONNALITES.md) | [Notifications](02-notifications.md) →
