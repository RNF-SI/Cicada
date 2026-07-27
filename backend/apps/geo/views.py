"""API de consultation du référentiel géographique administratif."""

from django.db.models import Prefetch
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

    def list(self, request):
        """Alias de `arbre`, pour que `/api/geo/zones/` soit utilisable tel quel."""
        return self.arbre(request)
