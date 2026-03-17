"""Vues API pour le référentiel INPG (géologie)."""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Inpg
from .serializers import InpgDetailSerializer, InpgListSerializer


class InpgViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API pour le référentiel géologique INPG.

    GET /api/inpg/<id_inpg>/         — détail d'un site
    GET /api/inpg/autocomplete/?search=<terme>&limit=20
    POST /api/inpg/validate-bulk/    — validation en masse
    """

    permission_classes = [IsAuthenticated]
    queryset = Inpg.objects.all()
    serializer_class = InpgDetailSerializer
    lookup_field = 'id_inpg'

    def get_serializer_class(self):
        if self.action == 'list':
            return InpgListSerializer
        return InpgDetailSerializer

    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """
        Autocomplete sur les sites INPG via trigrammes + unaccent.

        Paramètres :
        - search : terme de recherche (min 2 caractères)
        - limit : nombre max de résultats (défaut 20)
        """
        search = request.query_params.get('search', '').strip()
        if len(search) < 2:
            return Response([])

        limit = min(int(request.query_params.get('limit', 20)), 100)

        from django.db import connection
        with connection.cursor() as cursor:
            sql = """
                SELECT id_inpg, id_metier, lb_site, region,
                       departements, communes, interet_geol_principal
                FROM ref_inpg.inpg
                WHERE unaccent(COALESCE(lb_site, '') || ' ' || COALESCE(id_metier, ''))
                      ILIKE unaccent(%s)
                ORDER BY similarity(
                    unaccent(COALESCE(lb_site, '') || ' ' || COALESCE(id_metier, '')),
                    unaccent(%s)
                ) DESC
                LIMIT %s
            """
            params = [f'%{search}%', search, limit]
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(results)

    @action(detail=False, methods=['post'], url_path='validate-bulk')
    def validate_bulk(self, request):
        """
        Valide une liste d'entrées (id_inpg, id_metier, ou noms de sites)
        contre le référentiel INPG.

        Auto-détection du format :
        - Entrée numérique → recherche par id_inpg
        - Entrée texte type code (ex: "ARA0042") → recherche par id_metier
        - Entrée texte libre → recherche par nom de site (lb_site)

        POST body: {"items": ["42", "ARA0042", "Grotte de ...", ...]}
        Returns: {
            "found": [{"input": "...", "id_inpg": ..., "lb_site": ..., ...}],
            "not_found": [{"input": "...", "candidates": [...]}],
        }
        """
        items = request.data.get('items', [])
        if not items:
            return Response({'found': [], 'not_found': []})

        found = []
        not_found = []
        already_found_ids = set()

        result_fields = ('id_inpg', 'id_metier', 'lb_site', 'region',
                         'interet_geol_principal')

        for item in items:
            raw = str(item).strip()
            if not raw:
                continue

            match = None

            # 1) Numérique → id_inpg
            try:
                code_int = int(raw)
                match = Inpg.objects.filter(id_inpg=code_int).values(
                    *result_fields
                ).first()
            except (ValueError, TypeError):
                pass

            # 2) Recherche par id_metier (exact)
            if not match:
                match = Inpg.objects.filter(
                    id_metier__iexact=raw
                ).values(*result_fields).first()

            # 3) Recherche par nom de site (exact puis partiel)
            if not match:
                match = Inpg.objects.filter(
                    lb_site__iexact=raw
                ).values(*result_fields).first()

            if not match:
                match = Inpg.objects.filter(
                    lb_site__icontains=raw
                ).values(*result_fields).first()

            if match and match['id_inpg'] not in already_found_ids:
                entry = dict(match)
                entry['input'] = raw
                found.append(entry)
                already_found_ids.add(match['id_inpg'])
            elif not match:
                # Proposer des candidats proches
                candidates = []
                try:
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT id_inpg, lb_site, id_metier
                            FROM ref_inpg.inpg
                            WHERE unaccent(COALESCE(lb_site, '') || ' ' || COALESCE(id_metier, ''))
                                  ILIKE unaccent(%s)
                            ORDER BY similarity(
                                unaccent(COALESCE(lb_site, '') || ' ' || COALESCE(id_metier, '')),
                                unaccent(%s)
                            ) DESC
                            LIMIT 3
                        """, [f'%{raw}%', raw])
                        for row in cursor.fetchall():
                            candidates.append({
                                'id_inpg': row[0],
                                'lb_site': row[1],
                                'id_metier': row[2],
                            })
                except Exception:
                    pass
                not_found.append({'input': raw, 'candidates': candidates})

        return Response({'found': found, 'not_found': not_found})
