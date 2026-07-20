"""Vues API pour le référentiel CAMPanule."""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import CampanuleProtocole, AutocompleteProtocole
from .serializers import (
    CampanuleProtocoleDetailSerializer,
    CampanuleAutocompleteSerializer,
)


class CampanuleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API pour le référentiel CAMPanule (protocoles de collecte).

    GET /api/campanule/                        — liste paginée
    GET /api/campanule/<cd_protocole>/         — détail d'un protocole
    GET /api/campanule/autocomplete/?search=<terme>&limit=20
    """

    permission_classes = [IsAuthenticated]
    queryset = CampanuleProtocole.objects.all()
    serializer_class = CampanuleProtocoleDetailSerializer
    lookup_field = 'cd_protocole'

    def get_queryset(self):
        qs = CampanuleProtocole.objects.all()

        cible = self.request.query_params.get('cible')
        if cible:
            qs = qs.filter(cible__icontains=cible)

        categorie = self.request.query_params.get('categorie')
        if categorie:
            qs = qs.filter(categorie_prot__icontains=categorie)

        # Par défaut, exclure les obsolètes sauf si demandé
        include_obsolete = self.request.query_params.get(
            'include_obsolete', 'false'
        )
        if include_obsolete.lower() not in ('true', '1'):
            qs = qs.exclude(obsolete='true')

        return qs.order_by('lb_protocole_court')

    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """
        Autocomplete sur les protocoles CAMPanule via trigrammes + unaccent.

        Paramètres :
        - search : terme de recherche (optionnel — vide = liste alphabétique, #584)
        - limit : nombre max de résultats (défaut 20, max 100)
        - cible : filtre optionnel par cible (ex: "Oiseaux")
        """
        search = request.query_params.get('search', '').strip()

        limit = min(int(request.query_params.get('limit', 20)), 100)

        from django.db import connection
        with connection.cursor() as cursor:
            sql = """
                SELECT cd_protocole, search_name,
                       lb_protocole_court, lb_protocole_complet,
                       cible, categorie_prot, prot_auteur
                FROM ref_campanule.autocomplete_protocole
                WHERE 1 = 1
            """
            params = []

            if search:
                sql += """
                    AND (unaccent(lb_protocole_court) ILIKE unaccent(%s)
                         OR unaccent(lb_protocole_complet) ILIKE unaccent(%s))
                """
                params.extend([f'%{search}%', f'%{search}%'])

            cible = request.query_params.get('cible')
            if cible:
                sql += " AND cible ILIKE %s"
                params.append(f'%{cible}%')

            if search:
                sql += """
                    ORDER BY similarity(unaccent(lb_protocole_court), unaccent(%s)) DESC
                """
                params.append(search)
            else:
                # #584 — sans terme de recherche, on propose la liste alphabétique
                sql += """
                    ORDER BY COALESCE(lb_protocole_court, lb_protocole_complet) ASC
                """

            sql += " LIMIT %s"
            params.append(limit)

            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(results)
