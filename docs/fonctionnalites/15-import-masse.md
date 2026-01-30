# Import en masse de sites

### Comment ça marche

L'import en masse permet aux administrateurs de créer plusieurs sites en une seule opération à partir d'un fichier **GeoJSON** ou **CSV**. Cette fonctionnalité est accessible depuis la page "Mes Sites" via le bouton "Import en masse".

### Accès

| Rôle | Accès |
|------|-------|
| `super_admin` | Sites créés **actifs** immédiatement + relations automatiques |
| `admin_og` | Sites créés **inactifs** + demandes de validation générées |
| `utilisateur` | Pas d'accès (403 Forbidden) |

### Formats de fichiers supportés

#### GeoJSON (FeatureCollection)

Le fichier doit être un `FeatureCollection` contenant des `Feature` avec des propriétés et optionnellement des géométries (`Polygon` ou `MultiPolygon`).

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[2.35, 48.85], [2.36, 48.85], [2.36, 48.86], [2.35, 48.86], [2.35, 48.85]]]
      },
      "properties": {
        "nom_site": "Mon site",
        "id_inpn": "FR3600101",
        "type_site": "RNN",
        "surface": 150.5
      }
    }
  ]
}
```

#### CSV

Le fichier CSV utilise la virgule comme séparateur. L'encodage UTF-8 (avec ou sans BOM) est supporté. Le CSV **ne supporte pas les géométries**.

```csv
nom_site,id_inpn,id_local,type_site,surface,marin,outre_mer
Réserve du Lac,FR3600101,LOC-001,RNN,150.5,false,false
```

#### Contraintes communes

| Contrainte | Valeur |
|------------|--------|
| Taille maximale | 10 Mo |
| Extensions acceptées | `.geojson`, `.json`, `.csv` |
| Géométries supportées | `Polygon`, `MultiPolygon` (GeoJSON uniquement) |

### Fichiers exemples téléchargeables

Des fichiers exemples sont proposés directement dans le modal d'import :
- `import-sites-exemple.geojson` — 5 sites avec géométries polygones
- `import-sites-exemple.csv` — 5 sites sans géométrie

Ces fichiers sont stockés dans `frontend/src/assets/templates/`.

### Interface utilisateur (Modal stepper)

L'import se fait via un modal en 4 étapes avec un stepper Angular Material :

#### Étape 1 : Fichier

- Zone de glisser-déposer ou sélection de fichier
- Validation du format et de la taille
- Liens de téléchargement des fichiers exemples
- Note informative sur le support des géométries

#### Étape 2 : Correspondance des champs

Le système auto-détecte le mapping entre les propriétés du fichier et les champs de l'application. L'utilisateur peut ajuster manuellement chaque correspondance.

**Auto-détection :** Le système reconnaît les noms courants pour chaque champ :

| Champ cible | Noms reconnus automatiquement |
|-------------|-------------------------------|
| `nom_site` | `nom_site`, `nom`, `name`, `site_name`, `site`, `label`, `libelle` |
| `id_inpn` | `id_inpn`, `inpn`, `code_inpn`, `cdsinp` |
| `id_local` | `id_local`, `id`, `code`, `code_local`, `identifiant` |
| `type_site_id` | `type_site_id`, `type_site`, `type`, `id_type_site` |
| `surf_off` | `surf_off`, `surface`, `superficie`, `area`, `surface_ha` |
| `marin` | `marin`, `marine`, `milieu_marin` |
| `outre_mer` | `outre_mer`, `outremer`, `overseas` |

**Exemples de valeurs :** Le tableau affiche les 3 premières valeurs de chaque propriété pour aider l'utilisateur à identifier les correspondances.

**Re-validation :** Un bouton "Re-valider" permet de relancer la validation après modification du mapping.

#### Étape 3 : Vérification

Tableau de prévisualisation avec les sites parsés, affichant :
- Nom, INPN, ID local, surface, présence de géométrie
- Statut de chaque ligne (valide, erreur, doublon, avertissement)
- Checkbox de sélection (les lignes en erreur sont désactivées)
- Compteurs récapitulatifs (valides, erreurs, doublons, sélectionnés)

L'utilisateur peut sélectionner/désélectionner les sites à importer. Par défaut, tous les sites sans erreur et sans doublon sont sélectionnés.

#### Étape 4 : Résultats

Affiche le résultat de l'import :
- Nombre de sites créés, en attente de validation, en échec
- Tableau détaillé par site avec statut et message d'erreur éventuel
- Barre de progression pour les imports asynchrones (> seuil configurable)

### Validation des données

La validation s'effectue côté backend lors de l'étape de vérification. Voici les contrôles appliqués :

#### Champs obligatoires

| Champ | Règle |
|-------|-------|
| `nom_site` | Obligatoire, minimum 3 caractères |

#### Validation des valeurs

| Champ | Règle |
|-------|-------|
| `surf_off` | Doit être un nombre positif ou nul |
| `type_site_id` | Doit correspondre à un ID, mnémonique (ex: `RNN`, `PNR`, `ENS`) ou label de nomenclature existant. **Résolution insensible à la casse.** |
| `marin` / `outre_mer` | Accepte : `true/false`, `1/0`, `oui/non`, `yes/no`, `o/y` |
| `geometry` | Doit être un `Polygon` ou `MultiPolygon` GeoJSON valide |

#### Détection des doublons

| Type | Portée | Comportement |
|------|--------|--------------|
| Code INPN identique en base | Base de données | Erreur bloquante |
| Code INPN identique dans le fichier | Intra-batch | Erreur bloquante |
| Nom de site identique en base | Base de données (insensible à la casse) | Erreur bloquante |
| Nom de site identique dans le fichier | Intra-batch (insensible à la casse) | Erreur bloquante |

### Comportement à l'import

#### Super administrateur

```
Fichier → Validation → Import
                          ↓
          Site créé (active=True)
                          ↓
          CorRoleSite (referent=True, referent_valid=True)
                          ↓
          CorOgSite (principal=True, organisme de l'utilisateur)
```

Les sites sont immédiatement actifs et visibles. L'utilisateur est automatiquement référent.

#### Administrateur d'organisme

```
Fichier → Validation → Import
                          ↓
          Site créé (active=False)
                          ↓
          ValidationRequest (site_creation, pending)
                          ↓
          Notification aux validateurs (admin_og + super_admin)
```

Les sites sont créés inactifs et nécessitent une validation. Une `ValidationRequest` de type `site_creation` est créée pour chaque site.

### Gestion des erreurs

- **Transaction par site** : chaque site est importé dans sa propre transaction (`transaction.atomic()`). L'échec d'un site n'affecte pas les autres.
- **Erreurs globales** : si l'appel API échoue (erreur réseau, serveur), un message d'erreur global est affiché.
- **Détails par site** : le tableau des résultats montre le statut et le message d'erreur pour chaque site.

### Import asynchrone (Celery)

Pour les imports volumineux, le traitement s'exécute en arrière-plan via Celery :

1. L'API retourne immédiatement un `job_id`
2. Le frontend interroge périodiquement (`GET /api/users/sites/bulk_import_status/?job_id=X`) toutes les 2 secondes
3. Une barre de progression affiche l'avancement
4. Le polling s'arrête quand le statut passe à `completed` ou `failed`

**Modèle `BulkImportJob`** :

| Champ | Description |
|-------|-------------|
| `user` | Utilisateur ayant lancé l'import |
| `status` | `pending`, `processing`, `completed`, `failed` |
| `total_sites` | Nombre total de sites à importer |
| `processed_sites` | Nombre de sites traités |
| `created_sites` | Nombre de sites créés avec succès |
| `failed_sites` | Nombre de sites en échec |
| `validation_pending_sites` | Nombre de sites en attente de validation |

### Endpoints API

| Méthode | URL | Description |
|---------|-----|-------------|
| `POST` | `/api/users/sites/bulk_import_validate/` | Upload et validation du fichier |
| `POST` | `/api/users/sites/bulk_import_execute/` | Lancement de l'import |
| `GET` | `/api/users/sites/bulk_import_status/?job_id=X` | Statut d'un job asynchrone |

#### POST `/api/users/sites/bulk_import_validate/`

**Requête** : `multipart/form-data` avec :
- `file` : le fichier GeoJSON ou CSV
- `field_mapping` (optionnel) : JSON du mapping personnalisé

**Réponse** :
```json
{
  "detected_properties": ["nom", "inpn", "surface"],
  "suggested_mapping": {"nom": "nom_site", "inpn": "id_inpn"},
  "applied_mapping": {"nom": "nom_site", "inpn": "id_inpn"},
  "sites": [
    {
      "row_index": 0,
      "original_properties": {"nom": "Mon site", "inpn": "FR3600101"},
      "mapped_data": {"nom_site": "Mon site", "id_inpn": "FR3600101"},
      "geometry": { "type": "Polygon", "coordinates": [...] },
      "has_geometry": true,
      "errors": [],
      "warnings": [],
      "duplicate_info": null
    }
  ],
  "total": 5,
  "valid": 4,
  "errors": 1,
  "warnings": 0,
  "duplicates": 0
}
```

#### POST `/api/users/sites/bulk_import_execute/`

**Requête** : JSON avec :
- `sites` : liste des sites à importer (avec `row_index`, `original_properties`, `mapped_data`, `geometry`)
- `selected_indices` : liste des `row_index` sélectionnés

**Réponse** (sync) :
```json
{
  "async": false,
  "created": 3,
  "failed": 0,
  "validation_pending": 2,
  "details": [
    {"row_index": 0, "nom_site": "Mon site", "status": "created", "site_id": 42}
  ]
}
```

**Réponse** (async) :
```json
{
  "async": true,
  "job_id": 7,
  "message": "Import lancé en arrière-plan."
}
```

### Tests

La fonctionnalité est couverte par **38 tests** :

#### Backend (19 tests) — `backend/tests/integration/test_bulk_import.py`

| Classe | Tests | Couverture |
|--------|-------|------------|
| `TestBulkImportValidation` | 11 | Parsing GeoJSON/CSV, auto-détection mapping, mapping custom, validation nom court, doublon INPN en base, doublon INPN intra-batch, noms similaires, permissions |
| `TestBulkImportExecution` | 5 | Import sync, comportement super_admin vs admin_og, sélection partielle, rejet sélection vide |
| `TestBulkImportStatus` | 3 | Statut job, job inexistant, accès cross-user interdit |

#### Frontend (19 tests) — `bulk-site-import-modal.component.spec.ts`

| Section | Tests | Couverture |
|---------|-------|------------|
| Sélection fichier | 4 | Formats acceptés/rejetés, compteur features |
| Mapping | 3 | Propriétés détectées, suggestion mapping, modification |
| Prévisualisation | 5 | Status chips, checkboxes, toggle all, compteurs |
| Import | 5 | Appel API, résultats, erreurs, comptage sélection |
| Fermeture dialog | 2 | Retour null ou résultat selon import |

#### Fixtures — `backend/tests/fixtures/`

- `bulk_import_sample.geojson` — 5 features avec géométries
- `bulk_import_sample.csv` — 5 lignes de sites

### Fichiers techniques

| Fichier | Description |
|---------|-------------|
| `backend/apps/users/services_bulk_import.py` | Service de parsing, validation et import |
| `backend/apps/users/serializers_bulk_import.py` | Serializers DRF |
| `backend/apps/users/viewsets_org_sites.py` | Endpoints API (actions sur le ViewSet sites) |
| `backend/apps/users/tasks.py` | Tâche Celery pour import asynchrone |
| `backend/apps/users/models.py` | Modèle `BulkImportJob` |
| `backend/apps/users/migrations/0005_bulk_import_job.py` | Migration BDD |
| `frontend/.../bulk-site-import-modal/` | Composant Angular (modal stepper) |
| `frontend/src/app/core/services/admin.service.ts` | Méthodes `bulkImportValidate`, `bulkImportExecute`, `bulkImportStatus` |
| `frontend/src/app/core/models/admin.model.ts` | Interfaces TypeScript (BulkImport*) |
| `frontend/src/assets/templates/` | Fichiers exemples téléchargeables |

---

← [Plans de Gestion](14-plans.md) | [Index](../FONCTIONNALITES.md) |
