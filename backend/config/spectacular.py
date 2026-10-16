"""
Extensions drf-spectacular propres à CICADA.

Chargé par ``apps.core.apps.CoreConfig.ready()`` : les extensions s'enregistrent
à l'import, il faut donc que ce module soit importé avant la génération du schéma.

Deux cas que drf-spectacular ne sait pas décrire seul :

1. **Champs géométriques PostGIS mappés automatiquement par ``ModelSerializer``**
   (``PlanGestion.geometrie``, ``Enjeu.geom``, ``Operation.geom``,
   ``OperationAnnee.geom``, ``geology.Inpg.geom``…). ``rest_framework_gis`` n'est
   pas activé dans ``INSTALLED_APPS`` : DRF retombe sur ``rest_framework.fields.ModelField``,
   qui sérialise la géométrie en **EWKT** (``SRID=4326;MULTIPOLYGON (...)``) et
   accepte en écriture tout ce que ``GEOSGeometry()`` comprend (WKT, EWKT, GeoJSON
   sérialisé ou objet GeoJSON — la valeur est passée telle quelle au modèle).
   Sans extension, drf-spectacular avertit « could not resolve model field » et
   retombe sur ``string`` sans explication.

2. **``GeoJSONGeometryField``** (``apps.plans.serializers_operations``) : champ
   maison qui expose et accepte un objet GeoJSON. Il hérite de ``serializers.Field``,
   donc sans type connu.
"""
from django.contrib.gis.db.models.fields import BaseSpatialField
from drf_spectacular.extensions import OpenApiSerializerFieldExtension
from drf_spectacular.plumbing import build_basic_type
from drf_spectacular.types import OpenApiTypes

GEOJSON_GEOMETRY_TYPES = [
    'Point', 'MultiPoint', 'LineString', 'MultiLineString',
    'Polygon', 'MultiPolygon', 'GeometryCollection',
]
# Choix nommés dans ENUM_NAME_OVERRIDES : plusieurs serializers ont un champ
# `type` et drf-spectacular ne saurait pas nommer ces enums sans collision.
GEOJSON_FEATURE_TYPE_CHOICES = ['Feature']
GEOJSON_FEATURE_COLLECTION_TYPE_CHOICES = ['FeatureCollection']
GEOJSON_CRS_TYPE_CHOICES = ['name']

#: Schéma d'une géométrie GeoJSON (RFC 7946), en EPSG:4326.
GEOJSON_GEOMETRY_SCHEMA = {
    'type': 'object',
    'description': 'Géométrie GeoJSON (RFC 7946), coordonnées en EPSG:4326.',
    'required': ['type', 'coordinates'],
    'properties': {
        'type': {'type': 'string', 'enum': GEOJSON_GEOMETRY_TYPES},
        'coordinates': {
            'type': 'array',
            'items': {},
            'description': 'Tableau de coordonnées, imbriqué selon le type de géométrie.',
        },
    },
}

EWKT_DESCRIPTION = (
    'Géométrie PostGIS. En lecture : chaîne EWKT, par exemple '
    '`SRID=4326;MULTIPOLYGON (((...)))`.'
)
EWKT_WRITE_DESCRIPTION = (
    'Géométrie PostGIS. En écriture : chaîne WKT / EWKT, chaîne GeoJSON ou objet '
    'GeoJSON (tout ce que `GEOSGeometry()` accepte). Sans SRID explicite, '
    'EPSG:4326 est supposé.'
)


def geojson_geometry_schema(nullable=True, description=None):
    """Copie du schéma GeoJSON, nullable et avec description optionnelle."""
    schema = dict(GEOJSON_GEOMETRY_SCHEMA)
    if description:
        schema['description'] = description
    if nullable:
        schema['nullable'] = True
    return schema


class GisModelFieldExtension(OpenApiSerializerFieldExtension):
    """
    ``ModelField`` adossé à un champ spatial Django (sans rest_framework_gis).

    L'extension ne s'applique qu'aux ``ModelField`` dont ``model_field`` est un
    ``BaseSpatialField`` ; les autres ``ModelField`` restent traités par
    drf-spectacular.
    """

    target_class = 'rest_framework.fields.ModelField'
    match_subclasses = True

    @classmethod
    def _matches(cls, target) -> bool:
        if not super()._matches(target):
            return False
        return isinstance(getattr(target, 'model_field', None), BaseSpatialField)

    def map_serializer_field(self, auto_schema, direction):
        if direction == 'request':
            return {
                'oneOf': [
                    {**build_basic_type(OpenApiTypes.STR), 'description': 'WKT, EWKT ou GeoJSON sérialisé'},
                    geojson_geometry_schema(nullable=False),
                ],
                'description': EWKT_WRITE_DESCRIPTION,
            }
        # Le help_text du modèle écrase `description` ; l'exemple, lui, reste visible.
        return {
            **build_basic_type(OpenApiTypes.STR),
            'description': EWKT_DESCRIPTION,
            'example': 'SRID=4326;MULTIPOLYGON (((5.1 43.4, 5.2 43.4, 5.2 43.5, 5.1 43.4)))',
        }


class GeoJSONGeometryFieldExtension(OpenApiSerializerFieldExtension):
    """Champ maison exposé/accepté en GeoJSON (``geom_geojson``, ``geom_realisee``)."""

    target_class = 'apps.plans.serializers_operations.GeoJSONGeometryField'

    def map_serializer_field(self, auto_schema, direction):
        return geojson_geometry_schema(nullable=False)


# =============================================================================
# Briques réutilisables pour les `@extend_schema` des vues
# =============================================================================

from drf_spectacular.utils import OpenApiResponse, inline_serializer  # noqa: E402
from rest_framework import serializers  # noqa: E402

XLSX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
DOCX_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

#: Corps d'erreur ad hoc `{"error": "..."}` rendu par de nombreuses vues.
ERREUR_SERIALIZER = inline_serializer(
    name='Erreur',
    fields={'error': serializers.CharField(help_text='Message explicatif')},
)
#: Corps `{"message": "..."}`.
MESSAGE_SERIALIZER = inline_serializer(
    name='Message',
    fields={'message': serializers.CharField()},
)

REPONSE_400 = OpenApiResponse(response=ERREUR_SERIALIZER, description='Requête invalide')
REPONSE_401 = OpenApiResponse(description='Authentification requise')
REPONSE_403 = OpenApiResponse(description='Droits insuffisants')
REPONSE_404 = OpenApiResponse(description='Objet introuvable')


def reponse_binaire(content_type, description):
    """Réponse 200 binaire (xlsx, docx…) avec son content-type documenté."""
    return OpenApiResponse(
        response=OpenApiTypes.BINARY,
        description=f'{description} — `Content-Type: {content_type}`, '
                    'envoyé en pièce jointe (`Content-Disposition: attachment`).',
    )


def reponse_xlsx(description='Classeur Excel'):
    return reponse_binaire(XLSX_CONTENT_TYPE, description)


def reponse_docx(description='Document Word'):
    return reponse_binaire(DOCX_CONTENT_TYPE, description)


#: Corps multipart attendu par les imports de classeurs.
FICHIER_XLSX_REQUEST = {
    'multipart/form-data': inline_serializer(
        name='FichierXlsxUpload',
        fields={'file': serializers.FileField(help_text='Classeur .xlsx')},
    ),
}


from drf_spectacular.utils import extend_schema_field  # noqa: E402


@extend_schema_field(geojson_geometry_schema(nullable=True))
class GeoJSONGeometrySchemaField(serializers.JSONField):
    """Champ purement documentaire : une géométrie GeoJSON (ou null)."""


def geojson_feature_schema(properties_serializer, name='GeoJSONFeature'):
    """Serializer documentaire d'une `Feature` GeoJSON dont `properties` suit un serializer."""
    return inline_serializer(
        name=name,
        fields={
            'type': serializers.ChoiceField(choices=GEOJSON_FEATURE_TYPE_CHOICES),
            'geometry': GeoJSONGeometrySchemaField(allow_null=True),
            'properties': properties_serializer,
        },
    )


def geojson_feature_collection_schema(properties_serializer, crs=False, name='GeoJSONFeatureCollection'):
    """Serializer documentaire d'une `FeatureCollection` GeoJSON (option : membre `crs` EPSG:4326)."""
    fields = {
        'type': serializers.ChoiceField(choices=GEOJSON_FEATURE_COLLECTION_TYPE_CHOICES),
        'features': serializers.ListField(
            child=geojson_feature_schema(properties_serializer, name=name + 'Feature')),
    }
    if crs:
        fields['crs'] = inline_serializer(
            name=name + 'Crs',
            fields={
                'type': serializers.ChoiceField(choices=GEOJSON_CRS_TYPE_CHOICES),
                'properties': inline_serializer(
                    name=name + 'CrsProperties',
                    fields={'name': serializers.CharField(help_text='Toujours EPSG:4326')},
                ),
            },
        )
    return inline_serializer(name=name, fields=fields)


# ---------------------------------------------------------------------------
# Hook de post-traitement : un résumé pour chaque opération
# ---------------------------------------------------------------------------

def resume_depuis_description(result, generator, request, public):
    """Donne un ``summary`` aux opérations qui n'en ont pas, à partir de la
    première phrase de leur ``description`` (la docstring de la vue).

    Swagger UI n'affiche, dans la liste repliée, que le résumé : sans lui, les
    ~350 actions décrites par docstring n'apparaissent que par leur chemin. Les
    ``@extend_schema(summary=…)`` explicites sont conservés tels quels. Les
    docstrings de ViewSet commencent souvent par « ViewSet pour les … » : la
    tournure est aplatie en « … » pour rester un titre.
    """
    import re

    for chemin, operations in result.get('paths', {}).items():
        for methode, op in operations.items():
            if not isinstance(op, dict) or op.get('summary'):
                continue
            description = (op.get('description') or '').strip()
            if not description:
                continue
            premiere = description.splitlines()[0].strip()
            premiere = re.split(r'(?<=[.!?])\s', premiere, maxsplit=1)[0]
            premiere = re.sub(r'^(ViewSet|Vue|API|Endpoint)\s+(pour|de|des|du)\s+(la |les |le |l’|l\')?', '', premiere, flags=re.I)
            premiere = re.sub(r'^(GET|POST|PUT|PATCH|DELETE)\s+\S+\s*', '', premiere).strip(' .:—-')
            if not premiere:
                continue
            if len(premiere) > 110:
                premiere = premiere[:107].rstrip() + '…'
            op['summary'] = premiere[0].upper() + premiere[1:]
    return result
