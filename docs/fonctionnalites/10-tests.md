# Tests

### Comment ça marche

Les tests vérifient automatiquement que le code fonctionne correctement. Il existe 3 niveaux de tests :

| Niveau | Outil | Ce qu'il teste | Vitesse |
|--------|-------|----------------|---------|
| Unitaire backend | pytest | Fonctions/classes isolément | Rapide (~30s) |
| Unitaire frontend | Jest | Services/guards Angular isolément | Rapide (~15s) |
| **E2E (End-to-End)** | **Playwright** | **L'application complète dans un vrai navigateur** | **Lent (~5min)** |

### Backend (pytest)

#### Les factories

Au lieu de créer manuellement des données de test, on utilise des "usines" qui génèrent des objets réalistes.

**Exemple :** `UserFactory()` crée un utilisateur avec un email unique, un nom généré aléatoirement, un mot de passe hashé. On peut personnaliser : `UserFactory(email='custom@test.fr')`.

#### Les fixtures

Ce sont des "préparations" réutilisables.

**Exemple :** `authenticated_client` fournit un client API déjà connecté avec un utilisateur. Chaque test qui en a besoin le déclare en paramètre et pytest l'injecte automatiquement.

#### Tests unitaires vs intégration

| Type | Description |
|------|-------------|
| Unitaires | Testent une fonction/classe isolément, sans base de données réelle |
| Intégration | Testent le flux complet, avec vraie base de données, vraies requêtes HTTP |

#### Déroulement d'un test d'intégration API

1. Création des données de test via factories
2. Authentification du client de test
3. Envoi d'une requête HTTP (GET, POST, etc.)
4. Vérification du code de retour et du contenu de la réponse
5. Nettoyage automatique (rollback de la base)

### Frontend (Jest)

#### Mocking

On remplace les vrais services par des faux pour isoler ce qu'on teste.

**Exemple :** pour tester un guard de route, on remplace `AuthService` par un objet qui retourne `true` ou `false` selon le test.

#### TestBed

C'est l'environnement de test Angular. Il configure les dépendances (imports, providers) comme le ferait le vrai module, mais en version test.

### Tests E2E (Playwright)

Les tests E2E simulent un **vrai utilisateur** dans un navigateur Chromium. Ils s'exécutent contre le stack Docker complet (Django + PostgreSQL + Angular).

#### Ce que ça teste

| Catégorie | Exemples | Tests |
|-----------|----------|-------|
| Authentification | Login, logout, inscription | 13 |
| Admin Utilisateurs | Liste, filtres, activation, assign site | 15 |
| Admin Sites | Liste, création, organismes | 13 |
| Admin Validations | Liste, approbation, rejet | 6 |
| **Workflow validations** | **Demande → approbation/rejet multi-utilisateurs** | **8** |
| Admin Organismes + Dashboard | Liste, détail, stats | 7 |
| Contrôle d'accès | Pages autorisées/interdites par rôle | 13 |
| Navigation | Header, sidebar, liens | 4 |
| **Total** | | **~80** |

#### Comment ça marche (workflow de validation multi-utilisateurs)

Le test le plus intéressant simule un vrai échange entre deux utilisateurs :

1. **Utilisateur RNF** crée une demande d'accès à un site
2. **Utilisateur RNF** voit sa demande "en attente" sur sa page "Mes demandes"
3. **Super Admin** voit la demande sur la page "Validations"
4. **Super Admin** approuve la demande
5. **Utilisateur RNF** voit le statut passer à "approuvé"

Chaque utilisateur a sa propre session navigateur avec ses propres tokens JWT. On n'utilise pas l'impersonation : c'est le vrai flux multi-utilisateurs.

#### Exécution

```bash
cd frontend

npm run e2e          # Tous les tests (headless)
npm run e2e:ui       # Interface visuelle Playwright
npm run e2e:headed   # Tests visibles dans le navigateur
```

### CI/CD

À chaque push ou pull request sur main/develop, **et à chaque release** (tag `v*`), GitHub Actions :

1. Lance un conteneur avec PostgreSQL
2. Installe les dépendances
3. Exécute tous les tests backend (pytest)
4. Exécute tous les tests frontend (Jest)
5. **Exécute les tests E2E (Playwright) contre le stack Docker complet**
6. Génère les rapports de couverture
7. Bloque le merge si des tests échouent

Les tests E2E ne se lancent que si les tests backend passent (dépendance `needs: [backend-tests]`).

### Couverture

C'est le pourcentage de lignes de code exécutées par les tests.

| Stack | Type | Tests | Couverture | Objectif |
|-------|------|-------|----------:|----------:|
| Backend | Unitaires + Intégration | 317 | 56% | 80% |
| Frontend (Jest) | Unitaires | 55 | 7% | 70% |
| **Frontend (E2E)** | **End-to-End** | **~80** | **Voir détail** | **Toutes les pages** |

**Détail couverture E2E par fonctionnalité :**

| Fonctionnalité | Couverte | Détail |
|----------------|----------|--------|
| Login / Logout / Inscription | ✅ | Login valide/invalide, inscription, déconnexion |
| Admin Utilisateurs | ✅ | Liste, recherche, filtres, actions (activer/désactiver) |
| Admin Sites | ✅ | Liste, recherche, création, lien organismes |
| Admin Validations | ✅ | Liste, filtres, approbation, rejet |
| Workflow multi-utilisateurs | ✅ | Demande → vue admin → approbation → vérification |
| Admin Organismes | ✅ | Grille, détail, recherche, édition |
| Admin Dashboard | ✅ | Statistiques, message bienvenue |
| Contrôle d'accès par rôle | ✅ | 5 rôles × pages autorisées/interdites |
| Scope données par organisme | ✅ | RNF voit RNF, CEN voit CEN, super admin voit tout |
| Navigation | ✅ | Header, sidebar, liens inter-pages |

---

← [RGPD](09-rgpd.md) | [Index](../FONCTIONNALITES.md) | [Configuration du site](11-configuration.md) →
