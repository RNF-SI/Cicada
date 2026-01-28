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

| Entité | Quantité | Description |
|--------|----------|-------------|
| Modules | 4 | plans, sites, inventaires, zonages |
| Organismes | 5 | RNF, CEN AURA, DREAL, Parc Ecrins, OFB |
| Sites | 7 | Avec géométries PostGIS réelles |
| Utilisateurs | 14 | 7 actifs, 3 inactifs, 2 en attente, 2 RGPD |
| Plans de gestion | 8 | 5 actifs, 3 archivés |
| Groupes Django | 4 | Super Admin, Admin Organisme, Utilisateurs, Invités |
| PendingUser | 3 | Inscriptions en attente |
| Validations | 22+ | 11 types différents, statuts variés |
| Notifications | 21+ | 15 types, priorités variées |
| Logs d'erreur | 8 | WARNING, ERROR, CRITICAL |
| Logs d'activité | 25+ | public, admin, system |

### Architecture modulaire

```
backend/apps/core/management/commands/
├── seed_testdata.py              # Orchestrateur (~300 lignes)
└── seeders/
    ├── __init__.py               # Registry + validation des dépendances
    ├── base.py                   # Classe abstraite BaseSeeder
    ├── context.py                # SeederContext (partage de données)
    ├── signals.py                # Gestion des 28 signaux Django
    ├── modules_seeder.py
    ├── nomenclatures_seeder.py
    ├── groups_seeder.py
    ├── organismes_seeder.py
    ├── sites_seeder.py
    ├── users_seeder.py
    ├── plans_seeder.py
    ├── pending_users_seeder.py
    ├── validation_requests_seeder.py
    ├── notifications_seeder.py
    ├── error_logs_seeder.py
    └── activity_logs_seeder.py
```

### Composants clés

| Composant | Rôle |
|-----------|------|
| `BaseSeeder` | Classe abstraite avec `seed()`, `reset()`, `get_dry_run_summary()` |
| `SeederContext` | Partage de données entre seeders via `set()`, `get()`, `require()` |
| `signals_disabled()` | Context manager pour désactiver les signaux pendant le seeding |
| `SEEDER_CLASSES` | Liste ordonnée par dépendances (tri topologique) |

### Graphe de dépendances

```
modules, nomenclatures, groups, organismes (indépendants)
    │
    ├── sites (deps: organismes, nomenclatures)
    ├── users (deps: organismes, sites, groups)
    ├── pending_users (deps: organismes)
    ├── plans (deps: users, sites, nomenclatures)
    ├── validation_requests (deps: users, sites, plans, organismes)
    ├── notifications (deps: users, sites, plans, organismes, validation_requests)
    ├── error_logs (deps: users)
    └── activity_logs (deps: users, sites, plans, organismes, validation_requests)
```

### Option `--only`

Permet un seeding sélectif. Les dépendances sont résolues automatiquement.

**Exemple :** `--only=users,plans` exécute automatiquement :
1. `nomenclatures` (dépendance de sites et plans)
2. `groups` (dépendance de users)
3. `organismes` (dépendance de sites et users)
4. `sites` (dépendance de users et plans)
5. `users` (demandé)
6. `plans` (demandé)

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
