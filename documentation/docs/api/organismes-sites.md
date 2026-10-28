# Organismes et sites

Les **organismes** sont les structures gestionnaires (CEN, RNF, parcs…). Les **sites** sont les espaces protégés, portés par un ou plusieurs organismes dont un principal, avec une géométrie PostGIS stockée en WGS 84. Les sites sont identifiés par leur `slug` dans les URL.

## Organismes

| Endpoint | Rôle |
|----------|------|
| `GET/POST /api/users/organismes/` | Liste et création |
| `GET /api/users/organismes/public/` | Liste publique pour le formulaire d'inscription |
| `GET/PUT/PATCH/DELETE /api/users/organismes/{id}/` | Détail (utilisateurs, sites gérés, statistiques) |
| `GET /api/users/organismes/{id}/sites/` | Sites gérés par l'organisme |
| `POST /api/users/organismes/{id}/assign_site/`, `…/bulk_assign_sites/`, `…/unassign_site/` | Lier ou délier des sites (le retrait passe par une demande de validation) |
| `GET /api/users/organismes/stats/` | Statistiques |

## Sites

| Endpoint | Rôle |
|----------|------|
| `GET/POST /api/users/sites/` | Liste (filtres : type, organisme, actif…) et création avec workflow de validation |
| `GET/PUT/PATCH/DELETE /api/users/sites/{slug}/` | Détail, modification, suppression (avec avertissement sur les plans et utilisateurs rattachés) |
| `GET /api/users/sites/{slug}/geojson/`, `GET /api/users/sites/geojson_list/` | Géométries en GeoJSON (`Feature` / `FeatureCollection`) |
| `GET /api/users/sites/{slug}/export-geojson/`, `GET /api/users/sites/export-geojson/?ids=` | Fichier `.geojson` réimportable par l'import en masse : type en mnémonique, organismes par leur nom, sans identifiant local ni utilisateur |
| `GET /api/users/sites/search_all/`, `GET …/check_duplicates/` | Recherche dans tous les sites actifs ; détection des doublons (code INPN, noms similaires) |
| `POST /api/users/sites/{slug}/request_access/`, `…/request_referent/`, `…/request_org_link/` | Demandes d'accès, de rôle référent, de rattachement de son organisme |
| `POST /api/users/sites/{slug}/assign_user/`, `DELETE …/users/{user_pk}/`, `GET …/users/` | Membres et référents du site |
| `GET /api/users/sites/{slug}/organismes/`, `…/principal_organisme/`, `POST …/set_principal_organisme/` | Organismes gestionnaires et organisme principal |
| `POST /api/users/sites/{slug}/invite_user/`, `…/invite_organisme/` | Invitations par un référent |
| `POST /api/users/sites/bulk_import_validate/`, `…/bulk_import_execute/`, `GET …/bulk_import_status/` | Import en masse (GeoJSON ou CSV, 10 Mo au maximum) en trois temps : validation, exécution, suivi du job |
| `GET /api/users/sites/creation-validators/` | Qui validera une création de site, avant de la soumettre |
| `GET /api/geo/zones/` | Arbre régions → départements (découpage administratif `ref_geo`) |

## Règles

- **Unicité du code INPN** : `id_inpn` est unique. Créer un site avec un code déjà utilisé renvoie `400` avec le site existant ; `check_duplicates` permet de le vérifier avant.
- **Création soumise à validation** sauf pour le super administrateur : le site est créé mais sa validation suit le circuit des [demandes](notifications.md).
- **Rattachement géographique** : les régions et départements d'un site sont calculés par intersection PostGIS à l'enregistrement de la géométrie ; ils alimentent les filtres de l'exploration.
- **Géométries en écriture** : `geom` accepte un objet GeoJSON (`Polygon`, `MultiPolygon`) en WGS 84 ; un Shapefile zippé ou un GeoJSON peut aussi être téléversé à la création.

## Référence interactive

<swagger-ui src="openapi/organismes-sites.json"/>
