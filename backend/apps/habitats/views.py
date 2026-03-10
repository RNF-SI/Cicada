"""Vues API pour le référentiel HabRef."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Habref, Typoref, AutocompleteHabitat, HabrefCorrespHab
from .serializers import (
    HabrefDetailSerializer,
    TyporefSerializer,
    AutocompleteHabitatSerializer,
    HabrefCorrespHabSerializer,
)


class HabrefViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API pour le référentiel des habitats HabRef.

    GET /api/habref/habitat/<cd_hab>/  — détail d'un habitat
    GET /api/habref/autocomplete/?search=<terme>&cd_typo=<id>&limit=20
    GET /api/habref/typo/              — liste des typologies
    GET /api/habref/correspondance/<cd_hab>/  — correspondances
    """

    permission_classes = [IsAuthenticated]
    queryset = Habref.objects.all()
    serializer_class = HabrefDetailSerializer
    lookup_field = 'cd_hab'

    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """
        Autocomplete sur les habitats via trigrammes + unaccent.

        Paramètres :
        - search : terme de recherche (min 2 caractères)
        - cd_typo : filtre optionnel par code typologie
        - limit : nombre max de résultats (défaut 20)
        """
        search = request.query_params.get('search', '').strip()
        if len(search) < 2:
            return Response([])

        limit = min(int(request.query_params.get('limit', 20)), 100)

        from django.db import connection
        with connection.cursor() as cursor:
            sql = """
                SELECT cd_hab, cd_typo, lb_code, search_name,
                       lb_hab_fr, lb_hab_fr_complet, lb_typo, niveau
                FROM ref_habitats.autocomplete_habitat
                WHERE unaccent(search_name) ILIKE unaccent(%s)
            """
            params = [f'%{search}%']

            cd_typo = request.query_params.get('cd_typo')
            if cd_typo:
                sql += " AND cd_typo = %s"
                params.append(int(cd_typo))

            sql += """
                ORDER BY similarity(unaccent(search_name), unaccent(%s)) DESC
                LIMIT %s
            """
            params.extend([search, limit])

            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(results)

    @action(detail=False, methods=['get'])
    def typo(self, request):
        """Liste des typologies d'habitats."""
        typos = Typoref.objects.all().order_by('cd_typo')
        return Response(TyporefSerializer(typos, many=True).data)

    @action(
        detail=False,
        methods=['get'],
        url_path='correspondance/(?P<cd_hab>[0-9]+)',
    )
    def correspondance(self, request, cd_hab=None):
        """Correspondances entre typologies pour un habitat donné."""
        corresps = HabrefCorrespHab.objects.filter(
            cd_hab=cd_hab
        ).order_by('cd_typo_entre')
        return Response(
            HabrefCorrespHabSerializer(corresps, many=True).data
        )
