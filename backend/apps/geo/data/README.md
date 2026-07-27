# Données géographiques embarquées

## `departements.geojson`

Contours des 109 départements et collectivités françaises (métropole, DROM, COM, TAAF),
en WGS84 (EPSG:4326).

- **Source** : OpenDataSoft, jeu de données `georef-france-departement` (millésime 2025),
  lui-même dérivé du découpage administratif de l'IGN.
  <https://public.opendatasoft.com/explore/dataset/georef-france-departement/>
- **Traitement appliqué** : propriétés réduites à `dep_code`, `dep_name`, `reg_code`,
  `reg_name` ; coordonnées arrondies à 5 décimales (~1 m) ; JSON compacté.
  Le fichier passe ainsi de 1,1 Mo à ~550 Ko.

Les **régions** ne sont pas embarquées : elles sont reconstruites en base par agrégation
(`ST_Union`) des départements partageant le même `reg_code`, ce qui garantit que les deux
niveaux du filtre « zone géographique » sont géométriquement cohérents.

Le fichier est volontairement versionné dans le dépôt plutôt que téléchargé au démarrage :
CICADA est installé chez des clients dont les serveurs n'ont pas toujours d'accès Internet
sortant.

### Mise à jour

Ré-exporter le GeoJSON depuis OpenDataSoft, puis rejouer le script de nettoyage
(cf. l'en-tête de `apps/geo/management/commands/import_ref_geo.py`) et relancer :

```bash
docker compose exec web python manage.py import_ref_geo --force
```
