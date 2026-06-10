"""
Utilitaires géospatiaux partagés pour la gestion des géométries de sites.

La géométrie d'un site est stockée en `MultiPolygonField(srid=4326)`. Les
géométries arrivent depuis le frontend (carte Leaflet) ou depuis un import de
fichier (GeoJSON / Shapefile) et peuvent présenter des défauts courants :

- anneaux non fermés (le premier et le dernier point ne coïncident pas) ;
- auto-intersections (« nœud papillon ») ;
- trous dessinés comme polygones séparés qui se chevauchent (« donut ») ;
- SRID manquant ;
- type `Polygon` ou `GeometryCollection` au lieu de `MultiPolygon`.

`normalize_to_multipolygon` répare ces défauts de façon transparente et lève
une `GeometryError` avec un message clair en français lorsque la géométrie est
réellement inexploitable.
"""

import json

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.utils.translation import gettext_lazy as _

SRID = 4326


class GeometryError(ValueError):
    """Erreur de géométrie avec un message destiné à l'utilisateur final."""


def _close_rings(geojson):
    """Ferme les anneaux non fermés d'un GeoJSON Polygon / MultiPolygon.

    Modifie une copie du dictionnaire et la retourne. Les autres types sont
    renvoyés inchangés.
    """

    def fix_polygon(coords):
        fixed = []
        for ring in coords:
            if ring and list(ring[0]) != list(ring[-1]):
                ring = list(ring) + [ring[0]]
            fixed.append(ring)
        return fixed

    geom_type = geojson.get("type")
    if geom_type == "Polygon":
        geojson["coordinates"] = fix_polygon(geojson.get("coordinates", []))
    elif geom_type == "MultiPolygon":
        geojson["coordinates"] = [
            fix_polygon(polygon) for polygon in geojson.get("coordinates", [])
        ]
    return geojson


def normalize_to_multipolygon(value):
    """Convertit une géométrie (dict GeoJSON, str GeoJSON/WKT) en `MultiPolygon`
    valide en EPSG:4326.

    - ferme automatiquement les anneaux non fermés ;
    - répare les géométries invalides (auto-intersection, chevauchement) via
      `make_valid()` ;
    - force le SRID à 4326 ;
    - convertit `Polygon` et `GeometryCollection` (parties polygonales) en
      `MultiPolygon`.

    Lève `GeometryError` (message FR) si la valeur est illisible ou ne contient
    aucune surface exploitable.
    """
    if value is None:
        return None

    # Préparer le texte source : on ferme les anneaux côté dict avant le parse
    # (GEOS rejette sinon les anneaux non fermés au parsing).
    if isinstance(value, dict):
        raw = json.dumps(_close_rings(dict(value)))
    else:
        raw = str(value)

    try:
        geom = GEOSGeometry(raw)
    except Exception as exc:  # GEOSException, GDAL errors, JSON, etc.
        raise GeometryError(
            _("La géométrie fournie est invalide ou illisible (%(error)s).")
            % {"error": str(exc)}
        )

    if geom.empty:
        raise GeometryError(_("La géométrie fournie est vide."))

    if geom.srid is None:
        geom.srid = SRID

    # Réparer les invalidités topologiques (auto-intersection, trous mal formés…)
    if not geom.valid:
        try:
            geom = geom.make_valid()
        except Exception:
            raise GeometryError(
                _(
                    "La géométrie présente une erreur de topologie qui n'a pas "
                    "pu être corrigée automatiquement. Vérifiez qu'il n'y a pas "
                    "d'auto-intersection."
                )
            )
        if geom.srid is None:
            geom.srid = SRID

    # Convertir vers MultiPolygon
    if geom.geom_type == "MultiPolygon":
        result = geom
    elif geom.geom_type == "Polygon":
        result = MultiPolygon(geom)
    elif geom.geom_type == "GeometryCollection":
        polygons = [g for g in geom if g.geom_type == "Polygon"]
        if not polygons:
            raise GeometryError(
                _("La géométrie ne contient aucune surface (polygone) exploitable.")
            )
        result = MultiPolygon(polygons)
    else:
        raise GeometryError(
            _("La géométrie doit être un Polygon ou un MultiPolygon (reçu : %(type)s).")
            % {"type": geom.geom_type}
        )

    result.srid = SRID
    if result.empty:
        raise GeometryError(_("La géométrie fournie est vide après traitement."))
    return result
