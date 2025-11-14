# 🌿 Application de Gestion des Plans de Gestion

## 📋 Contexte du projet

Application web développée pour le CEN (Conservatoire d'Espaces Naturels) et RNF (Réserves Naturelles de France) permettant la gestion des plans de gestion d'espaces naturels avec support géospatial.


### Repository
- **GitHub** : https://github.com/RNF-SI/outil_plan_de_gestion
- **Branches** : main (production), develop (développement), feature/* (fonctionnalités)

## 🛠️ Stack technique

### Backend
- **Python 3.11+**
- **Django 5.0+** - Framework web principal
- **Django REST Framework 3.14+** - API REST
- **PostgreSQL 15+** - Base de données principale
- **PostGIS 3.3+** - Extension géospatiale
- **Redis 7+** - Cache et broker de messages
- **Celery** (optionnel V1) - Tâches asynchrones

### Frontend  
- **Angular 19+** - Framework SPA
- **TypeScript 5+** - Langage principal
- **Angular Material** - Composants UI
- **RxJS** - Programmation réactive
- **Leaflet** - Cartes interactives
- **SCSS** - Styles

### Infrastructure
- **Docker & Docker Compose** - Conteneurisation
- **GitHub Actions** - CI/CD
- **Apache** - Reverse proxy (production)
- **Gunicorn** - WSGI server (production)

### Outils de développement
- **Black** - Formatage Python
- **Flake8** - Linting Python  
- **isort** - Tri des imports Python
- **pytest** - Tests Python
- **ESLint** - Linting TypeScript
- **Prettier** - Formatage TypeScript
- **Karma/Jasmine** - Tests unitaires Angular
- **Cypress** - Tests E2E

## 📐 Architecture et structure

### Structure du projet
```
outil_plan_de_gestion/
├── backend/
│   ├── apps/
│   │   ├── authentication/    # Gestion auth et permissions
│   │   ├── users/             # Utilisateurs et organismes
│   │   ├── plans/             # Plans de gestion
│   │   ├── api/               # Endpoints API publics
│   │   └── core/              # Fonctionnalités communes
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   └── production.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── static/
│   ├── media/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── core/          # Services singleton
│   │   │   ├── shared/        # Composants partagés
│   │   │   ├── auth/          # Module authentification
│   │   │   ├── plans/         # Module plans de gestion
│   │   │   └── users/         # Module utilisateurs
│   │   ├── assets/
│   │   └── environments/
│   └── package.json
├── docker/
│   ├── nginx/
│   └── postgres/
├── docs/
├── .github/
│   └── workflows/
├── docker-compose.yml
├── .env.example
└── README.md
```

### Principes d'architecture

1. **Backend structuré avec API REST**
   - Le backend guide l'architecture (pas le front)
   - API RESTful avec Django REST Framework
   - Pagination directe selon les besoins
   - Design scalable et maintenable

2. **Separation of Concerns**
   - Apps Django modulaires et indépendantes
   - Services Angular pour la logique métier
   - Composants Angular pour la présentation

3. **Security First**
   - Authentification JWT pour l'API
   - Permissions basées sur les rôles

## 👥 Gestion des utilisateurs et rôles

### Hiérarchie des rôles

1. **Super Admin**
   - Accès total à l'application
   - Gestion de toutes les instances

2. **Administrateur Organisme (AdminOG)**
   - Gère les sites de son organisme
   - Gère les liens utilisateurs/sites
   - Peut nommer des référents
   - Peut modifier les plans de gestion de son OG
   - ⚠️ Ne valide/supprime pas les utilisateurs

3. **Référent**
   - Créateur d'un PG = référent par défaut
   - Seul le référent peut supprimer un PG
   - Plusieurs référents possibles par PG
   - Tout utilisateur peut créer un PG

4. **Utilisateur**
   - Droits en lecture par défaut
   - Peut devenir référent en créant un PG

### Authentification

**V0 - Authentification interne**
- Modèle User personnalisé Django
- Email comme identifiant unique
- JWT pour l'API

**V0 - Support Keycloak (optionnel)**
- django-allauth pour l'intégration
- Keycloak gère uniquement l'authentification
- La logique métier reste dans l'application

### Workflow d'onboarding

1. Connexion (interne ou Keycloak)
2. Si nouvel utilisateur → Formulaire d'informations
3. Sélection de l'organisme gestionnaire
4. Notification à l'admin de l'OG
5. Droits en lecture seule initialement
6. Validation admin → Droits complets

## 📊 Modèles de données principaux

class BibOrganismes(db.Model):
    """Table bib_organismes (avec 's') - nouvelle table à utiliser"""
    __tablename__ = 'bib_organismes'
    __table_args__ = {'schema': 'utilisateurs', 'extend_existing': True}

    id_organisme = db.Column(db.Integer, primary_key=True, nullable=False)
    uuid_organisme = db.Column(UUID(as_uuid=True), nullable=True)
    nom_organisme = db.Column(db.Unicode, nullable=True)
    adresse_organisme = db.Column(db.Unicode, nullable=True)
    cp_organisme = db.Column(db.Unicode, nullable=True)
    ville_organisme = db.Column(db.Unicode, nullable=True)
    tel_organisme = db.Column(db.Unicode, nullable=True)
    fax_organisme = db.Column(db.Unicode, nullable=True)
    email_organisme = db.Column(db.Unicode, nullable=True)
    url_organisme = db.Column(db.Unicode, nullable=True)
    url_logo = db.Column(db.Unicode, nullable=True)
    id_parent = db.Column(db.Integer, db.ForeignKey('utilisateurs.bib_organismes.id_organisme'), nullable=True)
    additional_data = db.Column(db.dialects.postgresql.JSONB, server_default='{}', nullable=True)
    meta_create_date = db.Column(db.DateTime, nullable=True, default=datetime.datetime.now)
    meta_update_date = db.Column(db.DateTime, nullable=True, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    espaces_proteges = db.relationship('CorOgEp', back_populates="organisme")
    duerps = db.relationship('Duerp', back_populates="organisme")

class CorRoleEp(db.Model):
    __tablename__ = 'cor_role_ep'
    __table_args__ = {'schema': 'utilisateurs'}

    id_ep = db.Column(db.Integer, db.ForeignKey('referentiels.t_espace_protege.id_ep'), primary_key=True, nullable=False)
    id_role = db.Column(db.Integer, db.ForeignKey('utilisateurs.t_roles.id_role'), primary_key=True, nullable=False)
    referent = db.Column(db.Boolean)
    referent_valid = db.Column(db.Boolean)
    conservateur = db.Column(db.Boolean, default=False)

    espace_protege = db.relationship("EspaceProtege", back_populates="utilisateurs")
    utilisateur = db.relationship("Role", back_populates="espaces_proteges")

class CorOgEp(db.Model):
    __tablename__ = 'cor_ep_og'
    __table_args__ = {'schema': 'utilisateurs'}

    id_ep = db.Column(db.Integer, db.ForeignKey('referentiels.t_espace_protege.id_ep'), primary_key=True, nullable=False)
    uuid_og = db.Column(UUID(as_uuid=True), db.ForeignKey('utilisateurs.bib_organismes.uuid_organisme'), primary_key=True, nullable=False)
    principal = db.Column(db.Boolean)

    espace_protege = db.relationship("EspaceProtege", back_populates="organismes_gestionnaires")
    organisme = db.relationship("BibOrganismes", back_populates="espaces_proteges")



### User dans la table t_roles du schéma utilisateurs (extends AbstractUser)
```python
exemple: 
class Role(db.Model):
    __tablename__ = 't_roles'
    __table_args__ = {'schema': 'utilisateurs', 'extend_existing': True}

    groupe = db.Column(db.Boolean, default=False, nullable=False)
    id_role = db.Column(db.Integer, primary_key=True, nullable=False)
    uuid_role = db.Column(UUID(as_uuid=True), nullable=False, unique=True)
    identifiant = db.Column(db.String(100), nullable=True)
    nom_role = db.Column(db.String(50), nullable=True)
    prenom_role = db.Column(db.String(50), nullable=True)
    desc_role = db.Column(db.Text, nullable=True)
    pass_role = db.Column("pass", db.String(100), nullable=True, key="pass")
    pass_plus = db.Column(db.Text, nullable=True)
    email = db.Column(db.String(250), nullable=True)
    id_organisme = db.Column(db.Integer, db.ForeignKey('utilisateurs.bib_organismes.id_organisme'), nullable=True)
    remarques = db.Column(db.Text, nullable=True)
    active = db.Column(db.Boolean, default=True, nullable=True)
    champs_addi = db.Column(db.Text, nullable=True)
    date_insert = db.Column(db.DateTime, nullable=True)
    date_update = db.Column(db.DateTime, nullable=True)

    organisme = db.relationship('BibOrganismes')
    sites = db.relationship('CorRoleSite')

```

### OrganismeGestionnaire appelée BibOrganismes dans le schéma utilisateurs
```python
exemple:
class BibOrganismes(db.Model):
    """Table bib_organismes (avec 's') - nouvelle table à utiliser"""
    __tablename__ = 'bib_organismes'
    __table_args__ = {'schema': 'utilisateurs', 'extend_existing': True}

    id_organisme = db.Column(db.Integer, primary_key=True, nullable=False)
    uuid_organisme = db.Column(UUID(as_uuid=True), nullable=True)
    nom_organisme = db.Column(db.Unicode, nullable=True)
    adresse_organisme = db.Column(db.Unicode, nullable=True)
    cp_organisme = db.Column(db.Unicode, nullable=True)
    ville_organisme = db.Column(db.Unicode, nullable=True)
    tel_organisme = db.Column(db.Unicode, nullable=True)
    fax_organisme = db.Column(db.Unicode, nullable=True)
    email_organisme = db.Column(db.Unicode, nullable=True)
    url_organisme = db.Column(db.Unicode, nullable=True)
    url_logo = db.Column(db.Unicode, nullable=True)
    id_parent = db.Column(db.Integer, db.ForeignKey('utilisateurs.bib_organismes.id_organisme'), nullable=True)
    additional_data = db.Column(db.dialects.postgresql.JSONB, server_default='{}', nullable=True)
    meta_create_date = db.Column(db.DateTime, nullable=True, default=datetime.datetime.now)
    meta_update_date = db.Column(db.DateTime, nullable=True, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    sites = db.relationship('Sites', back_populates="organisme")
```


### PlanGestion dans la table t_plan_gestion du schéma plans_de_gestion
```python 
exemple:
class PlanGestion(db.Model):
    __tablename__ = 't_plan_gestion'
    __table_args__ = {'schema': 'general'}

    id_pg = db.Column(db.Integer, primary_key=True)
    id_cdr = db.Column(db.Integer)
    nom = db.Column(db.String)
    gestion_partagee = db.Column(db.Boolean)
    # autres_ep supprimé - utiliser cor_ep_pg pour les plans multisites
    gestion_partagee_aire_protegee = db.Column(db.Boolean)
    autres_aire_protegee = db.Column(db.String)
    annee_debut = db.Column(db.Integer)
    annee_fin = db.Column(db.Integer)
    ct88 = db.Column(db.Boolean)
    # Le risque incendie est-il pris en compte dans le plan de gestion ?
    risque_incendie = db.Column(db.Boolean)
    id_evaluation = db.Column(db.Integer, db.ForeignKey('referentiels.t_nomenclatures.id_nomenclature'))
    id_redacteur_type = db.Column(db.Integer, db.ForeignKey('referentiels.t_nomenclatures.id_nomenclature'))
    redacteur_nom = db.Column(db.String)
    commentaire = db.Column(db.Text)
    date_ajout = db.Column(db.DateTime, default=datetime.datetime.now)
    date_maj = db.Column(db.DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)
    id_utilisateur_ajout = db.Column(db.Integer, db.ForeignKey('utilisateurs.t_roles.id_role'))
    id_utilisateur_maj = db.Column(db.Integer, db.ForeignKey('utilisateurs.t_roles.id_role'))

    evaluation = db.relationship('Nomenclature', foreign_keys=[id_evaluation])
    redacteur_type = db.relationship('Nomenclature', foreign_keys=[id_redacteur_type])
    utilisateur_ajout = db.relationship('Role', foreign_keys=[id_utilisateur_ajout])
    utilisateur_maj = db.relationship('Role', foreign_keys=[id_utilisateur_maj])

    espaces_proteges = db.relationship(
        "CorEpPg", back_populates = "plan_de_gestion", passive_deletes=True
    )
    fichiers = db.relationship("CorPgFichier", back_populates = "plan_de_gestion", cascade="all, delete-orphan")
```

### Sites dans la table t_sites du schéma référentiel
exemple:
```python 
class Site(db.Model):
    __tablename__ = 't_espace_protege'
    __table_args__ = {'schema': 'referentiels'}

    id_site = db.Column(db.Integer, primary_key=True)
    id_local = db.Column(db.String)
    id_inpn = db.Column(db.String)
    id_type_site = db.Column(db.Integer, db.ForeignKey('referentiels.t_nomenclatures.id_nomenclature'))
    date_crea = db.Column(db.Date)
    nom_site = db.Column(db.String)
    jonction_nom = db.Column(db.String)
    surf_off = db.Column(db.Float)
    geom = db.Column(Geometry(geometry_type='MULTIPOLYGON', srid=4326))
    geom_pt = db.Column(Geometry(geometry_type='POINT', srid=4326))
    modif_adm = db.Column(db.Date)
    modif_geo = db.Column(db.Date)
    marin = db.Column(db.Boolean)
    outre_mer = db.Column(db.Boolean)
    active = db.Column(db.Boolean)

    plans_de_gestion = db.relationship("CorSitePg", back_populates = "site")
    type_site = db.relationship('Nomenclature')
    utilisateurs = db.relationship("CorRoleSite", back_populates = "site")
    organismes_gestionnaires = db.relationship("CorOgEp", back_populates = "site")
```





## 🔄 API et synchronisation

### Système de tokens
- Tokens avec expiration configurable
- Gestion dans l'admin Django
- Rate limiting par token
- Rotation périodique

### Endpoints publics
- `/api/public/pg/` - Plans de gestion publics
- `/api/public/sites/` - Sites publics
- Format GeoJSON pour les données géospatiales

### Synchronisation inter-instances
- Script CRON nocturne (2h du matin)
- Basé sur `last_update` et UUID
- Tracking consenti des instances (RGPD)

## 📝 Standards de code et bonnes pratiques

### Python/Django

1. **Style**
   - PEP 8 strict
   - Black pour le formatage (ligne de 88 caractères)
   - isort pour les imports
   - Type hints quand pertinent

2. **Naming conventions**
   - Classes: PascalCase
   - Functions/variables: snake_case
   - Constants: UPPER_SNAKE_CASE
   - Private: _leading_underscore

3. **Django specific**
   - Une app = une responsabilité
   - Fat models, thin views
   - Utiliser les managers pour les requêtes complexes
   - Serializers pour la validation

### TypeScript/Angular

1. **Style**
   - Angular Style Guide officiel
   - ESLint + Prettier
   - Strict mode activé

2. **Naming conventions**
   - Components: PascalCase + Component suffix
   - Services: PascalCase + Service suffix
   - Interfaces: PascalCase avec I prefix
   - Enums: PascalCase

3. **Angular specific**
   - Composants petits et focalisés
   - Services pour la logique métier
   - RxJS: unsubscribe systématique
   - OnPush strategy quand possible

### Git

1. **Branches**
   - `main` : Production
   - `develop` : Développement
   - `feature/[issue-number]-[description]`
   - `bugfix/[issue-number]-[description]`
   - `hotfix/[description]`

2. **Commits (Conventional Commits)**
   ```
   feat: add user authentication #7
   fix: resolve database connection #23
   docs: update API documentation
   test: add unit tests for user model
   chore: update dependencies
   refactor: simplify user service
   style: format code with black
   perf: optimize database queries
   ```

3. **Pull Requests**
   - Une PR = Une issue
   - Description claire du changement
   - Tests inclus
   - Review obligatoire avant merge

## 🧪 Tests

### Backend
- **Couverture minimum** : 80%
- **pytest** + pytest-django
- Tests unitaires pour models, views, serializers
- Tests d'intégration pour les workflows
- Factory Boy pour les fixtures

### Frontend
- **Couverture minimum** : 70%
- **Karma/Jasmine** pour les tests unitaires
- **Cypress** pour les tests E2E
- Tests des services obligatoires
- Tests des guards et interceptors

### Structure des tests
```python
# Backend
def test_should_[action]_when_[condition]:
    # Given
    # When  
    # Then

# Frontend
it('should [action] when [condition]', () => {
    // Arrange
    // Act
    // Assert
});
```

## 🌍 Internationalisation (i18n)

- **Langues supportées** : Français (défaut), Anglais
- **Backend** : Django i18n framework
- **Frontend** : Angular i18n avec @angular/localize
- **Clés de traduction** : format `module.context.message`

## 🔒 Sécurité et RGPD

### Sécurité
- HTTPS obligatoire en production
- Headers de sécurité (CSP, HSTS, X-Frame-Options)
- Validation stricte des entrées
- Échappement des sorties
- Rate limiting sur les API
- Secrets en variables d'environnement

### RGPD
- Consentement explicite pour le tracking
- Droit à l'effacement (endpoint dédié)
- Export des données personnelles
- Logs d'audit
- Minimisation des données
- Chiffrement des données sensibles

## 🚀 Environnements et déploiement

### Environnements
1. **Local** : Docker Compose, DEBUG=True
2. **Staging** : Pré-production, données de test
3. **Production** : Données réelles, DEBUG=False

### Variables d'environnement clés
```env
# Django
SECRET_KEY=
DEBUG=
ALLOWED_HOSTS=

# Database
DATABASE_URL=postgis://user:pass@host:port/db

# Redis
REDIS_URL=redis://host:6379/0

# API
API_TOKEN_EXPIRY_DAYS=30

# Email
EMAIL_BACKEND=
EMAIL_HOST=
EMAIL_PORT=
```

### Docker
- Multi-stage builds
- Images Alpine quand possible
- Health checks sur tous les services
- Volumes pour les données persistantes

## 📊 Métriques de qualité

### Code
- Coverage > 80% (backend) / 70% (frontend)
- Pas de code dupliqué (DRY)
- Complexité cyclomatique < 10
- Pas de TODO/FIXME en production

### Performance
- Temps de réponse API < 200ms
- Lighthouse score > 90
- Bundle size < 500KB (initial)
- Lazy loading des modules Angular

### Accessibilité
- WCAG 2.1 niveau AA
- Support clavier complet
- ARIA labels appropriés
- Contraste suffisant

## 🔄 Workflow de développement

1. **Prendre une issue** assignée
2. **Créer une branche** depuis develop
3. **Développer** avec commits atomiques
4. **Tester** localement (unit + integration)
5. **Push** et créer une PR vers develop
6. **Review** par un pair
7. **Merge** après approbation
8. **Deploy** automatique sur staging
9. **Validation** sur staging
10. **Merge** develop → main (release)

## 📚 Documentation

### À maintenir à jour
- README.md : Instructions d'installation
- CONTRIBUTING.md : Guide de contribution
- API.md : Documentation des endpoints
- ARCHITECTURE.md : Décisions d'architecture
- DEPLOYMENT.md : Guide de déploiement

### Docstrings
```python
# Backend - Google style
def calculate_area(geometry: Polygon) -> float:
    """Calculate the area of a polygon.
    
    Args:
        geometry: The polygon geometry.
        
    Returns:
        The area in hectares.
        
    Raises:
        ValueError: If geometry is invalid.
    """
```

```typescript
// Frontend - JSDoc
/**
 * Calculate the area of a polygon
 * @param geometry - The polygon geometry
 * @returns The area in hectares
 * @throws {Error} If geometry is invalid
 */
```

## ⚠️ Points d'attention spécifiques

1. **Toujours utiliser PostGIS** pour les opérations géométriques
2. **Pagination obligatoire** pour les listes > 20 items
3. **Soft delete** pour les données importantes
4. **Audit trail** pour les modifications de PG
5. **Cache Redis** pour les données fréquemment accédées
6. **Transactions** pour les opérations critiques
7. **Optimistic locking** pour les éditions concurrentes

## 🎯 Objectifs V0 (MVP)

### Fonctionnalités essentielles
- ✅ Authentification et gestion des utilisateurs
- ✅ CRUD des plans de gestion
- ✅ Gestion des organismes et sites
- ✅ Permissions par rôle
- ✅ API publique avec tokens
- ✅ Interface Angular minimale
- ✅ Support géospatial basique
- ✅ Keycloak

### Hors scope V0
- ❌ Workflow de validation complet (V1)
- ❌ Synchronisation inter-instances (V1)
- ❌ Exports PDF avancés (V1)
- ❌ Notifications temps réel (V2)

## 💡 Conseils pour Claude Code

1. **Commencer simple** puis itérer
2. **Tests d'abord** (TDD) quand possible
3. **Commits fréquents** avec messages clairs
4. **Code auto-documenté** > commentaires
5. **YAGNI** - You Aren't Gonna Need It
6. **DRY** - Don't Repeat Yourself
7. **SOLID** principles
8. **Refactorer** régulièrement

## 📞 Ressources et contacts

- **Repo** : https://github.com/RNF-SI/outil_plan_de_gestion
- **Project Board** : https://github.com/RNF-SI/outil_plan_de_gestion/projects/1
- **Issues** : https://github.com/RNF-SI/outil_plan_de_gestion/issues

---

*Ce document doit être mis à jour à chaque décision technique importante.*
