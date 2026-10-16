"""API de consultation du référentiel géographique administratif."""

from django.db.models import Prefetch
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AreaType, LArea
from .serializers import RegionSerializer


class ZoneGeographiqueViewSet(viewsets.ViewSet):
    """
    Arbre régions → départements, pour le filtre « zone géographique ».

    Référentiel public et volumineux à recalculer côté client : il est renvoyé
    d'un bloc, sans pagination, et sans géométries (un filtre n'affiche que des
    libellés).
    """

    @extend_schema(
        operation_id='geo_zones_arbre_retrieve',
        summary="Arbre régions → départements",
        description=(
            "Référentiel administratif (ref_geo) actif, régions triées par nom et "
            "départements par code, sans géométrie ni pagination. Les `id_area` "
            "renvoyés sont ceux attendus par le filtre `zones` de l'exploration. "
            "Identifiants **locaux** à l'instance : seuls les `code` (INSEE) sont "
            "stables entre instances."
        ),
        responses={200: RegionSerializer(many=True),
                   401: OpenApiResponse(description="Authentification requise.")},
        tags=['geo'],
    )
    @action(detail=False, methods=['get'], url_path='arbre')
    def arbre(self, request):
        regions = (
            LArea.objects.filter(
                id_type__type_code=AreaType.REGION, enable=True
            )
            .prefetch_related(
                Prefetch(
                    'children',
                    queryset=LArea.objects.filter(enable=True).only(
                        'id_area', 'area_code', 'area_name', 'parent'
                    ),
                )
            )
            .order_by('area_name')
            .only('id_area', 'area_code', 'area_name')
        )
        return Response(RegionSerializer(regions, many=True).data)

    @extend_schema(
        operation_id='geo_zones_list',
        summary="Arbre régions → départements (alias de `arbre/`)",
        description="Même réponse que `/api/geo/zones/arbre/`.",
        responses={200: RegionSerializer(many=True),
                   401: OpenApiResponse(description="Authentification requise.")},
        tags=['geo'],
    )
    def list(self, request):
        """Alias de `arbre`, pour que `/api/geo/zones/` soit utilisable tel quel."""
        return self.arbre(request)
