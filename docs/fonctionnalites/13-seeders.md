# Données de test (Seeders)

> ⚠️ **Attention : Section réservée aux développeurs**
>
> Cette section décrit l'architecture interne du système de génération de données de test.

### Comment ça marche

La commande `seed_testdata` permet de créer un jeu de données cohérent pour le développement et les tests. Elle utilise une **architecture modulaire** avec des seeders indépendants qui respectent un graphe de dépendances.

### Commandes disponibles

```bash
# Créer toutes les données de test
docker compose exec web python manage.py seed_testdata

# Supprimer les données de test
docker compose exec web python manage.py seed_testdata --reset

# Prévisualiser ce qui serait créé (sans modification)
docker compose exec web python manage.py seed_testdata --dry-run

# Seeding sélectif (avec résolution automatique des dépendances)
docker compose exec web python manage.py seed_testdata --only=users,plans
```

### Données créées

Les volumes et les cas de recette (comptes, plans « Ventilation … », chaînes de versions, plans composites, suivi en cours…) évoluent à chaque lot : la liste à jour est la section **« Test Data Available » du `CLAUDE.md`**. Tous les comptes ont le mot de passe `Test123!`.

Les grandes familles :

| Seeder | Ce qu'il crée |
|--------|---------------|
| `modules`, `groups`, `organismes`, `sites`, `users` | Socle : organismes (dont un bureau d'études), sites avec géométries, comptes de chaque rôle |
| `plans` | Plans de gestion de tous les statuts, chaînes de versions, prolongations, circuit CSRPN, mi-parcours |
| `enjeux`, `minimal_plans` | Arborescences complètes et plans minimaux |
| `realisations`, `rh` | Suivi saisi, postes et temps de travail |
| `ventilation_plans` | Un plan par mode de ventilation budgétaire, leurs jumeaux validés et les plans composites (mêmes totaux : 139 800 €, 269 j) |
| `pending_users`, `validation_requests`, `notifications`, `error_logs`, `activity_logs` | Inscriptions, demandes de validation, notifications et journaux |

### Architecture modulaire

```
backend/apps/core/management/commands/
├── seed_testdata.py              # Orchestrateur
└── seeders/
    ├── __init__.py               # SEEDER_CLASSES + validation des dépendances
    ├── base.py                   # Classe abstraite BaseSeeder
    ├── context.py                # SeederContext (partage de données)
    ├── signals.py                # Désactivation des signaux Django pendant le seed
    ├── _coherence.py             # Règles communes aux seeders d'actions (#763)
    ├── _geo_helpers.py           # Emprises prévues / réalisées
    ├── modules_seeder.py, groups_seeder.py, organismes_seeder.py
    ├── sites_seeder.py, users_seeder.py, plans_seeder.py
    ├── enjeux_seeder.py, minimal_plans_seeder.py
    ├── realisations_seeder.py, rh_seeder.py, ventilation_plans_seeder.py
    ├── pending_users_seeder.py, validation_requests_seeder.py
    └── notifications_seeder.py, error_logs_seeder.py, activity_logs_seeder.py
```

### Composants clés

| Composant | Rôle |
|-----------|------|
| `BaseSeeder` | Classe abstraite avec `seed()`, `reset()`, `get_dry_run_summary()` |
| `SeederContext` | Partage de données entre seeders via `set()`, `get()`, `require()` |
| `signals_disabled()` | Context manager pour désactiver les signaux pendant le seeding |
| `SEEDER_CLASSES` | Liste ordonnée par dépendances (tri topologique) |

### Graphe de dépendances

Les nomenclatures ne sont pas un seeder : elles sont importées au démarrage (`import_nomenclatures`).

```
modules, groups, organismes (indépendants)
    │
    ├── sites (organismes)
    ├── users (organismes, sites, groups)
    ├── pending_users (organismes)
    ├── plans (users, sites)
    │     ├── enjeux (plans)
    │     │     ├── minimal_plans (enjeux)
    │     │     └── realisations (enjeux)
    │     │           └── rh (minimal_plans, realisations)
    │     └── ventilation_plans (plans)
    ├── validation_requests (users, sites, plans, organismes)
    ├── notifications (… validation_requests)
    ├── error_logs (users)
    └── activity_logs (users, sites, plans, organismes, validation_requests)
```

### Option `--only`

Permet un seeding sélectif. Les dépendances sont résolues automatiquement.

**Exemple :** `--only=users,plans` exécute aussi `organismes`, `groups` et `sites`, dans l'ordre des dépendances.

### Garde-fous

- Le seed est **idempotent** : il se relance sans doublon. Les années sont ancrées sur l'année courante.
- Il refuse les réglages de production (`--instance-de-production` pour une instance de démonstration).
- Sur une base neuve, il reconstruit l'index de recherche et crée la configuration de l'instance avant de dater l'acceptation des CGU des comptes de test.
- `tests/apps/core/test_seed_coherence_ventilation.py` relance le seed complet deux fois et vérifie chaque action contre les règles actuelles : un nouveau seeder d'actions doit le passer.

### Ajouter un nouveau seeder

1. Créer `seeders/mon_seeder.py` héritant de `BaseSeeder`
2. Définir l'attribut `name` (identifiant unique)
3. Définir l'attribut `dependencies` (liste des seeders requis)
4. Implémenter les méthodes :
   - `seed()` : crée les données, retourne les objets créés
   - `reset()` : supprime les données, retourne le nombre supprimé
   - `get_dry_run_summary()` : retourne un résumé pour `--dry-run`
5. Ajouter la classe dans `SEEDER_CLASSES` de `__init__.py` (respecter l'ordre des dépendances)

### Gestion des signaux

Pendant le seeding, 28 signaux Django sont désactivés pour éviter :
- Les notifications automatiques indésirables
- Les logs d'activité en double
- Les effets de bord des handlers de signaux

Le context manager `signals_disabled()` gère cette désactivation/réactivation proprement.

### Fichiers concernés

| Fichier | Rôle |
|---------|------|
| `backend/apps/core/management/commands/seed_testdata.py` | Orchestrateur principal |
| `backend/apps/core/management/commands/seeders/` | Dossier des seeders modulaires |
| `backend/apps/core/activity_signals.py` | 18 signaux d'activité (désactivés) |
| `backend/apps/notifications/signals.py` | 8 signaux de notifications (désactivés) |
| `backend/apps/users/signals.py` | 7 signaux utilisateurs (désactivés) |

---

---

← [Page Exploration](12-exploration.md) | [Index](../FONCTIONNALITES.md) | →
