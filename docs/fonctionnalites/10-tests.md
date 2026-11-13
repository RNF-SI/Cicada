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

Authentification et accès par rôle, administration (utilisateurs, sites, organismes, validations), arborescence des enjeux (CRUD, hiérarchie, suppressions en cascade, droits), création et vues des plans, actions et suivis (saisie, ventilation maximale, planification annuelle), inventaires, exploration, import en masse, profil, activité, notifications. La liste des fichiers et leur nombre de tests sont tenus dans [TESTING.md](../TESTING.md).

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

### Filets transverses (backend)

| Dossier / test | Ce qu'il protège |
|----------------|------------------|
| `tests/integrite/` | Aucune perte de données à l'aller-retour GET → PATCH, suppressions en cascade relues (`cascades_relues.txt`), migrations sans retour listées, matrice des droits d'écriture (`test_droits_ecriture.py`) et des comptes |
| `tests/integrite/test_canari.py` | Aucune donnée sensible (budget, RH, mesures, personnes) ne sort vers l'exploration ou le hub |
| `tests/apps/core/test_seed_coherence_ventilation.py` | Le jeu d'essai suit les règles actuelles de programmation |
| `tests/federation/bench.py` (hors CI) | Contrat, scénarios et parité entre CICADA et le hub, sur les briques réellement lancées |

### CI/CD

À chaque push ou pull request sur `main` / `develop`, et à chaque tag `v*`, GitHub Actions (`.github/workflows/tests.yml`) :

1. lance les tests backend (pytest, avec PostgreSQL/PostGIS) ;
2. lance les tests frontend (Jest) et le contrôle de types, E2E compris ;
3. lance les tests E2E Playwright contre le stack Docker, une fois les tests backend passés ;
4. construit la documentation en mode strict (`docs-build`).

Un test en échec bloque le merge. Les tests de packaging (`packaging/`) ne tournent pas en CI : ils demandent une VM (voir `packaging/TESTING.md`).

### Couverture

Les chiffres de couverture et le nombre de tests changent à chaque lot : voir [TESTING.md](../TESTING.md).

---

← [RGPD](09-rgpd.md) | [Index](../FONCTIONNALITES.md) | [Configuration](11-configuration.md) →
