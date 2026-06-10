"""
Tests unitaires pour `apps.users.geo_utils.normalize_to_multipolygon`.

Couvre la normalisation/réparation des géométries de site :
- conversion vers MultiPolygon (Polygon, GeometryCollection) ;
- fermeture automatique des anneaux non fermés ;
- réparation des géométries invalides (auto-intersection, chevauchement) ;
- forçage du SRID à 4326 ;
- conservation des trous (donut valide) ;
- messages d'erreur clairs pour les entrées inexploitables.
"""
import json

import pytest
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon

from apps.users.geo_utils import GeometryError, normalize_to_multipolygon


# Géométries de référence ----------------------------------------------------

def _polygon():
    return {
        "type": "Polygon",
        "coordinates": [[[4.70, 46.90], [4.70, 46.92], [4.73, 46.92],
                         [4.73, 46.90], [4.70, 46.90]]],
    }


def _multipolygon():
    return {
        "type": "MultiPolygon",
        "coordinates": [[[[4.70, 46.90], [4.70, 46.92], [4.73, 46.92],
                          [4.73, 46.90], [4.70, 46.90]]]],
    }


def _donut():
    """MultiPolygon avec un vrai trou (anneau intérieur)."""
    return {
        "type": "MultiPolygon",
        "coordinates": [[
            [[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]],
            [[3, 3], [3, 6], [6, 6], [6, 3], [3, 3]],
        ]],
    }


# Tests : type / structure ----------------------------------------------------

class TestNormalizeTypeCoercion:

    def test_none_returns_none(self):
        assert normalize_to_multipolygon(None) is None

    def test_multipolygon_passthrough(self):
        geom = normalize_to_multipolygon(_multipolygon())
        assert isinstance(geom, MultiPolygon)
        assert geom.geom_type == "MultiPolygon"
        assert geom.num_geom == 1

    def test_polygon_is_wrapped_into_multipolygon(self):
        geom = normalize_to_multipolygon(_polygon())
        assert isinstance(geom, MultiPolygon)
        assert geom.geom_type == "MultiPolygon"
        assert geom.num_geom == 1

    def test_geometrycollection_extracts_polygons(self):
        gc = {
            "type": "GeometryCollection",
            "geometries": [
                {"type": "Polygon", "coordinates": _polygon()["coordinates"]},
                {"type": "Point", "coordinates": [4.71, 46.91]},
            ],
        }
        geom = normalize_to_multipolygon(gc)
        assert geom.geom_type == "MultiPolygon"
        assert geom.num_geom == 1  # seul le polygone est conservé

    def test_accepts_geojson_string(self):
        geom = normalize_to_multipolygon(json.dumps(_multipolygon()))
        assert isinstance(geom, MultiPolygon)


# Tests : SRID ----------------------------------------------------------------

class TestNormalizeSrid:

    def test_srid_forced_on_multipolygon(self):
        geom = normalize_to_multipolygon(_multipolygon())
        assert geom.srid == 4326

    def test_srid_forced_on_converted_polygon(self):
        # `MultiPolygon(polygon)` perd le SRID : on vérifie qu'il est restauré.
        geom = normalize_to_multipolygon(_polygon())
        assert geom.srid == 4326

    def test_srid_forced_after_make_valid(self):
        bowtie = {
            "type": "MultiPolygon",
            "coordinates": [[[[0, 0], [10, 10], [10, 0], [0, 10], [0, 0]]]],
        }
        geom = normalize_to_multipolygon(bowtie)
        assert geom.srid == 4326


# Tests : réparation ----------------------------------------------------------

class TestNormalizeRepair:

    def test_unclosed_ring_is_auto_closed(self):
        """Anneau non fermé (import Shapefile/GeoJSON) -> fermé automatiquement."""
        unclosed = {
            "type": "MultiPolygon",
            "coordinates": [[[[4.70, 46.90], [4.70, 46.92], [4.73, 46.92],
                              [4.73, 46.90]]]],  # dernier point != premier
        }
        geom = normalize_to_multipolygon(unclosed)
        assert geom.geom_type == "MultiPolygon"
        assert geom.valid

    def test_unclosed_ring_on_polygon_type(self):
        poly = {
            "type": "Polygon",
            "coordinates": [[[4.70, 46.90], [4.70, 46.92], [4.73, 46.92],
                             [4.73, 46.90]]],
        }
        geom = normalize_to_multipolygon(poly)
        assert geom.valid

    def test_self_intersection_is_repaired(self):
        """Nœud papillon -> rendu valide par make_valid()."""
        bowtie = {
            "type": "MultiPolygon",
            "coordinates": [[[[0, 0], [10, 10], [10, 0], [0, 10], [0, 0]]]],
        }
        geom = normalize_to_multipolygon(bowtie)
        assert geom.valid

    def test_overlapping_parts_are_repaired(self):
        """Donut dessiné comme deux polygones séparés qui se chevauchent."""
        overlap = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]],
                [[[3, 3], [3, 6], [6, 6], [6, 3], [3, 3]]],
            ],
        }
        geom = normalize_to_multipolygon(overlap)
        assert geom.geom_type == "MultiPolygon"
        assert geom.valid

    def test_valid_donut_hole_is_preserved(self):
        """Un vrai donut valide doit conserver son trou."""
        geom = normalize_to_multipolygon(_donut())
        assert geom.geom_type == "MultiPolygon"
        assert geom.valid
        # le polygone conserve un anneau intérieur (le trou)
        assert geom[0].num_interior_rings == 1

    def test_already_valid_geometry_unchanged_topology(self):
        geom = normalize_to_multipolygon(_multipolygon())
        assert geom.valid
        assert geom.num_geom == 1


# Tests : erreurs -------------------------------------------------------------

class TestNormalizeErrors:

    def test_linestring_raises_geometry_error(self):
        with pytest.raises(GeometryError) as exc:
            normalize_to_multipolygon({"type": "LineString",
                                       "coordinates": [[0, 0], [1, 1]]})
        assert "Polygon" in str(exc.value)

    def test_point_raises_geometry_error(self):
        with pytest.raises(GeometryError):
            normalize_to_multipolygon({"type": "Point", "coordinates": [4.7, 46.9]})

    def test_garbage_string_raises_geometry_error(self):
        with pytest.raises(GeometryError):
            normalize_to_multipolygon("ceci n'est pas une géométrie")

    def test_geometrycollection_without_polygon_raises(self):
        gc = {
            "type": "GeometryCollection",
            "geometries": [{"type": "Point", "coordinates": [4.7, 46.9]}],
        }
        with pytest.raises(GeometryError):
            normalize_to_multipolygon(gc)

    def test_error_message_is_human_readable(self):
        with pytest.raises(GeometryError) as exc:
            normalize_to_multipolygon({"type": "LineString",
                                       "coordinates": [[0, 0], [1, 1]]})
        # message en français, exploitable côté UI
        assert "géométrie" in str(exc.value).lower()
