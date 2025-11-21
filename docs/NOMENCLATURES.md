# Nomenclatures pour Plans de Gestion

Ce document explique l'intégration et la gestion des nomenclatures dans l'outil Plan de Gestion.

## Vue d'ensemble

Les nomenclatures standardisent les référentiels utilisés dans les plans de gestion des espaces protégés. Elles sont organisées en types et nomenclatures individuelles avec support de la hiérarchisation.

## Structure des données

### Types de nomenclatures (`referentiels.bib_nomenclatures_types`)

Table des catégories de nomenclatures :
- **id_type** : Identifiant unique
- **mnemonique** : Code mnémonique du type  
- **label** : Libellé descriptif
- **definition** : Définition détaillée
- **source** : Source des données
- **statut** : Statut de validation

### Nomenclatures (`referentiels.t_nomenclatures`)

Table des valeurs de nomenclatures :
- **id_nomenclature** : Identifiant unique
- **id_type** : Référence vers le type
- **mnemonique** : Code mnémonique
- **label** : Libellé descriptif
- **definition** : Définition détaillée
- **hierarchy** : Code hiérarchique (optionnel)
- **actif** : Indicateur d'activation

## Installation automatique

### Première installation

Lors d'un démarrage Docker, les nomenclatures sont automatiquement initialisées :

```bash
docker-compose up -d
```

Le processus inclut :
1. Migrations Django
2. **Import des nomenclatures** ← Nouveau
3. Création du superutilisateur
4. Génération des données de test

### Mise à jour manuelle

Pour mettre à jour les nomenclatures :

```bash
# Depuis l'hôte
docker-compose exec web python import_nomenclatures.py

# Ou depuis le container
python import_nomenclatures.py
```

## Scripts disponibles

### `import_nomenclatures.py`
Script principal d'import des nomenclatures.
- Supprime les tables existantes
- Recrée la structure complète  
- Importe toutes les données depuis les fichiers SQL

### `test_nomenclatures.py`
Script de vérification des nomenclatures importées.
- Affiche les statistiques d'import
- Liste des exemples par type
- Validation de l'intégrité des données

## Fichiers de données

### `nomenclatures_data/backup_bib_nomenclatures.sql`
Fichier SQL contenant les INSERT pour les types de nomenclatures.

### `nomenclatures_data/backup_nomenclatures.sql`
Fichier SQL contenant les INSERT pour les nomenclatures individuelles.

## Administration Django

### Accès à l'interface
- **URL** : http://localhost:8000/admin/
- **Section** : Core > Nomenclatures / Types de nomenclatures
- **Permissions** : Consultation pour tous, modification pour superusers uniquement

### Fonctionnalités disponibles
- **Consultation** des nomenclatures et types
- **Recherche** par mnémonique, label ou définition
- **Filtrage** par type, statut, source
- **Navigation** entre types et nomenclatures liées

## Utilisation dans l'application

### Modèles Django

```python
from apps.core.models import TypeNomenclature, Nomenclature

# Récupérer un type
type_espace = TypeNomenclature.objects.get(mnemonique='Espace naturel')

# Récupérer des nomenclatures d'un type
espaces = Nomenclature.objects.filter(id_type=type_espace)

# Recherche par mnémonique
rnn = Nomenclature.objects.get(mnemonique='RNN')
```

### API REST

Les nomenclatures sont disponibles via l'API Django REST Framework :
- `GET /api/nomenclatures/types/` - Liste des types
- `GET /api/nomenclatures/` - Liste des nomenclatures
- Filtrage et recherche supportés

## Types de nomenclatures disponibles

### Espaces protégés
- Types d'espaces naturels (RNN, RNR, RNC, PPRN...)
- Statuts d'évaluation des plans

### Gestion administrative  
- Sources de financement hiérarchisées
- Types de contrats et emplois
- Catégories de rédacteurs

### Activités réglementées
- Activités autorisées/encadrées/interdites
- Classifications hiérarchiques détaillées
- Modalités d'encadrement

## Développement

### Modification des données

Pour ajouter de nouvelles nomenclatures :

1. **Modifier les fichiers SQL** dans `nomenclatures_data/`
2. **Réexécuter l'import** : `python import_nomenclatures.py`
3. **Vérifier l'import** : `python test_nomenclatures.py`

### Ajout de nouveaux types

```python
# Via l'admin Django ou directement en SQL
INSERT INTO referentiels.bib_nomenclatures_types 
VALUES (999, 'NOUVEAU_TYPE', 'Nouveau type de nomenclature', ...);
```

### Modèles personnalisés

Les modèles Django utilisent `managed = False` pour éviter les conflits avec la gestion manuelle par SQL.

## Troubleshooting

### Import échoue
```bash
# Vérifier les fichiers SQL
ls -la nomenclatures_data/

# Réexécuter l'import
docker-compose exec web python import_nomenclatures.py
```

### Tables manquantes
```bash
# Le script recrée automatiquement les tables
python import_nomenclatures.py
```

### Données corrompues
```bash
# Réimport complet
python import_nomenclatures.py

# Vérification
python test_nomenclatures.py
```

## Architecture technique

### Schéma PostgreSQL
Les nomenclatures utilisent le schéma `referentiels` pour l'organisation logique.

### Gestion des clés étrangères
Relations automatiquement maintenues entre types et nomenclatures.

### Performance
- Index automatiques sur les clés primaires
- Optimisations `select_related` dans l'admin Django

### Intégration Docker
Import automatique au démarrage pour les nouvelles installations.