# Page Exploration

### Comment ça marche

La page Exploration offre aux visiteurs non connectés une vue d'ensemble des espaces naturels protégés gérés dans l'application. C'est une page d'entrée "vitrine" accessible publiquement.

### Objectif

- Présenter les statistiques globales (nombre de sites, plans, etc.)
- Permettre une navigation vers la découverte des sites
- Servir de page d'accueil alternative pour les visiteurs

### Contenu affiché

| Élément | Source |
|---------|--------|
| Nombre total de sites actifs | API `/api/public/stats/` |
| Nombre de plans de gestion | API `/api/public/stats/` |
| Répartition par type de site | API `/api/public/stats/` |
| Image de fond | Configuration du site |

### Accès

- **Route** : `/exploration`
- **Permission** : Publique (pas d'authentification requise)
- **Lien depuis** : Page d'accueil (visiteurs non connectés)

### Composants utilisés

- `ExplorationComponent` : Composant principal
- `HeaderComponent` : Navigation commune
- `PublicStatsService` : Récupération des statistiques publiques

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `frontend/.../exploration/exploration.component.ts` | Composant principal |
| `frontend/.../exploration/exploration.component.html` | Template |
| `frontend/.../exploration/exploration.component.scss` | Styles |
| `frontend/.../exploration/exploration.routes.ts` | Configuration des routes |

---

---

← [Configuration du site](11-configuration.md) | [Index](../FONCTIONNALITES.md) | [Données de test](13-seeders.md) →
