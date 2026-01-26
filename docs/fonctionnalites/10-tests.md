# Tests

### Comment ça marche

Les tests vérifient automatiquement que le code fonctionne correctement.

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

### CI/CD

À chaque push ou pull request sur main/develop, GitHub Actions :

1. Lance un conteneur avec PostgreSQL
2. Installe les dépendances
3. Exécute tous les tests backend
4. Exécute tous les tests frontend
5. Génère un rapport de couverture
6. Bloque le merge si des tests échouent

### Couverture

C'est le pourcentage de lignes de code exécutées par les tests.

| Stack | Couverture actuelle | Objectif |
|-------|--------------------:|----------:|
| Backend | 56% | 80% |
| Frontend | 7% | 70% |

---

---

← [RGPD](09-rgpd.md) | [Index](../FONCTIONNALITES.md) | [Configuration du site](11-configuration.md) →
