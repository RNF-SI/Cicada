"""
Helpers géographiques partagés par les seeders.

But : centraliser le format des géométries d'opérations pour qu'il soit
identique à celui des sites (Site.geom = MultiPolygon SRID 4326), comme
demandé fonctionnellement.
"""
from django.contrib.gis.geos import MultiPolygon, Polygon


# Coordonnées approximatives (lon, lat) des principaux sites/réserves utilisés
# pour seeder. Permet d'éviter des polygones flottants au milieu de l'océan.
_CENTERS_BY_CODE_PREFIX = {
    'CAM':  (4.45, 43.55),     # Camargue
    'AR':   (6.95, 45.99),     # Aiguilles Rouges
    'VER':  (5.35, 44.95),     # Vercors-Écrins
    'REM':  (6.27, 46.77),     # Lac de Remoray (et Lacs/zones humides continentales)
    'REM2': (6.27, 46.77),     # Lac de Remoray (chaîne minimal_plans)
    'BRG':  (-1.07, 45.92),    # Marais de Brouage
    'SCA':  (8.55, 42.36),     # Scandola
}

_DEFAULT_CENTER = (2.21, 46.23)  # France centrale (fallback)


def _square_polygon(lon: float, lat: float, half_size: float) -> Polygon:
    """Polygone carré centré sur (lon, lat), arête = 2 × half_size degrés."""
    coords = [
        (lon - half_size, lat - half_size),
        (lon + half_size, lat - half_size),
        (lon + half_size, lat + half_size),
        (lon - half_size, lat + half_size),
        (lon - half_size, lat - half_size),
    ]
    return Polygon(coords, srid=4326)


def make_operation_geom(code_operation: str | None, idx: int = 0) -> MultiPolygon:
    """
    Construit un MultiPolygon SRID 4326 pour une opération, format identique
    aux géométries de sites (Site.geom = MultiPolygonField).

    Args:
        code_operation: code de l'opération (CAM-SE01, BRG-CS01, ...) — son
            préfixe sert à localiser le polygone sur la bonne zone géographique.
        idx: index de l'opération pour décaler légèrement la position et la
            taille (variété visuelle pour les démos).

    Returns:
        MultiPolygon SRID 4326 prêt à être affecté à Operation.geom.
    """
    prefix = (code_operation or '').split('-')[0].upper()
    lon, lat = _CENTERS_BY_CODE_PREFIX.get(prefix, _DEFAULT_CENTER)

    # Décalage déterministe pour éviter de superposer les polygones d'un même
    # plan. ~0.005° ≈ 500 m.
    dx = (idx % 4) * 0.005
    dy = (idx // 4 % 4) * 0.005
    center_lon = lon + dx
    center_lat = lat + dy

    # Taille variable (entre ~500 m et ~2 km de côté) pour la diversité.
    half_size = 0.005 + (idx % 5) * 0.003

    polygon = _square_polygon(center_lon, center_lat, half_size)
    return MultiPolygon(polygon, srid=4326)
