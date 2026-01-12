# Guide Développeur

Guide pratique pour le développement sur l'Outil Plan de Gestion.

> **Voir aussi** : [README.md](../README.md) pour l'installation | [TESTING.md](TESTING.md) pour les tests

---

## Commandes essentielles

### Docker

```bash
# Démarrer
docker-compose up -d

# Arrêter
docker-compose down

# Reconstruire après modification des dépendances
docker-compose build web

# Logs en temps réel
docker-compose logs -f web
```

### Backend Django

```bash
# Migrations
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate

# Shell Django
docker-compose exec web python manage.py shell

# Créer des données de test
docker-compose exec web python manage.py seed_testdata
docker-compose exec web python manage.py seed_testdata --reset  # Supprimer

# Tests
docker-compose exec web pytest tests/
```

### Frontend Angular

```bash
cd frontend
npm install
npm start           # Serveur dev sur http://localhost:4200
npm run build       # Build production
npm test            # Tests Jest
```

---

## Système de permissions

### Rôles utilisateur

| Rôle | Niveau | Description |
|------|--------|-------------|
| **Super Admin** | `super_admin` | Accès total à toute l'application |
| **Admin Organisme** | `admin_og` | Gestion de son organisme et ses utilisateurs |
| **Utilisateur** | `utilisateur` | Accès standard, peut être référent |

### Notion de référent

Un utilisateur devient **référent** s'il est :
- Référent d'un **site** (`CorRoleSite.referent = True`)
- Référent d'un **plan de gestion** (`PlanGestion.referents`)

Le statut de référent donne des droits supplémentaires sur les ressources concernées.

### Vérification des permissions

```python
# Dans le code Python
user.is_super_admin()      # Est super admin ?
user.is_admin_organisme()  # Est admin de son organisme ?
user.is_referent()         # Est référent (site ou plan) ?

# Permissions spécifiques
user.can_manage_site(site)           # Peut gérer ce site ?
user.can_manage_organisme(organisme) # Peut gérer cet organisme ?
```

### Classes de permission DRF

```python
from apps.users.permissions import IsSuperAdmin, IsAdminOrganisme, IsReferent

class MyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsSuperAdmin]
```

### Décorateurs

```python
from apps.users.decorators import require_super_admin, require_admin_organisme

@require_super_admin
def admin_only_view(request):
    pass
```

---

## Logs

### Visualiser les logs

```bash
# Logs filtrés (requêtes et erreurs)
docker-compose logs -f web | grep -E "(Request|AUDIT|ERROR)"

# Tous les logs
docker-compose logs -f web
```

### Configuration

| Variable | Description | Défaut |
|----------|-------------|--------|
| `LOG_LEVEL` | DEBUG, INFO, WARNING, ERROR | INFO |
| `LOG_DIR` | Répertoire des fichiers de logs | /app/logs |
| `LOG_SQL` | Activer les logs SQL (true/false) | false |

### Fichiers de logs (production)

| Fichier | Contenu |
|---------|---------|
| `django.log` | Logs généraux |
| `error.log` | Erreurs uniquement |
| `audit.log` | Actions utilisateur (POST/PUT/DELETE) |

### Correlation ID

Chaque requête HTTP reçoit un UUID unique dans le header `X-Correlation-ID`. Ce même ID apparaît dans tous les logs liés à cette requête, facilitant le debugging.

```
[2026-01-12 15:41:05] INFO http f4f5f562-5b94-4a32-a741-18ff6e055737 Request started
[2026-01-12 15:41:05] INFO apps f4f5f562-5b94-4a32-a741-18ff6e055737 User login
[2026-01-12 15:41:05] INFO http f4f5f562-5b94-4a32-a741-18ff6e055737 Request completed
```

---

## Internationalisation (i18n)

### Frontend (Angular)

**Fichier de traductions** : `frontend/src/assets/i18n/fr.json`

```html
<!-- Dans les templates -->
<h1>{{ 'admin.users.title' | translate }}</h1>
<input [placeholder]="'common.actions.search' | translate">
```

```typescript
// Dans le code TypeScript
import { TranslateService } from '@ngx-translate/core';

this.translate.instant('common.actions.save');
```

**Structure des clés** :
- `common.actions.*` : Actions (save, cancel, delete...)
- `common.status.*` : Statuts (active, pending...)
- `admin.users.*` : Gestion utilisateurs
- `admin.plans.*` : Gestion plans

### Backend (Django)

```python
from django.utils.translation import gettext_lazy as _

class MonModel(models.Model):
    nom = models.CharField(_("Nom"), max_length=100)

    class Meta:
        verbose_name = _("Mon modèle")
```

---

## Styles et Design System

### Couleurs principales

| Nom | Code | Usage |
|-----|------|-------|
| Primary | `#025359` | Éléments principaux |
| Yellow | `#FEC180` | Accents secondaires |
| Salmon | `#F5B399` | Accents |
| Terra Cotta | `#B74D5D` | Alertes, accents |
| Pale Green | `#C0E3CF` | Succès, validation |

### Couleurs de score

| Score | Code | Icône |
|-------|------|-------|
| Très mauvais | `#FF7579` | `<app-score-icon level="very-bad">` |
| Mauvais | `#FA9965` | `<app-score-icon level="bad">` |
| Neutre | `#F7D35C` | `<app-score-icon level="neutral">` |
| Bon | `#82DB8A` | `<app-score-icon level="good">` |
| Très bon | `#81C9D8` | `<app-score-icon level="very-good">` |

### Classes CSS utiles

```html
<!-- Spacing -->
<div class="m-md p-lg">...</div>  <!-- margin medium, padding large -->

<!-- Couleurs de texte -->
<span class="text-primary">Texte primaire</span>
<span class="text-success">Succès</span>
<span class="text-error">Erreur</span>

<!-- Status chips -->
<mat-chip class="status-success">Validé</mat-chip>
<mat-chip class="status-warning">En attente</mat-chip>
<mat-chip class="status-error">Refusé</mat-chip>
```

### Icônes

**Flaticon Uicons** (classe `fi-rr-*`) :
```html
<i class="fi-rr-user"></i>
<i class="fi-rr-document"></i>
<i class="fi-rr-settings"></i>
```

### Fichiers SCSS

| Fichier | Contenu |
|---------|---------|
| `_variables.scss` | Couleurs, spacing, typography |
| `_typography.scss` | Styles de texte |
| `_material-overrides.scss` | Personnalisation Angular Material |
| `_components.scss` | Composants custom (jauges, tuiles...) |
| `_filters.scss` | Filtres et pagination |

---

## Documentation associée

| Document | Description |
|----------|-------------|
| [README.md](../README.md) | Installation et démarrage rapide |
| [API_USERS_GUIDE.md](API_USERS_GUIDE.md) | API Utilisateurs |
| [API_PLANS_GUIDE.md](API_PLANS_GUIDE.md) | API Plans de gestion |
| [API_ORGANISMES_SITES_GUIDE.md](API_ORGANISMES_SITES_GUIDE.md) | API Organismes et Sites |
| [NOMENCLATURES.md](NOMENCLATURES.md) | Référentiels de données |
| [TESTING.md](TESTING.md) | Guide des tests |
