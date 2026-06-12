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

        is_numeric = search.isdigit()

        from django.db import connection
        # Recherche par mots : chaque mot doit apparaître (sous-chaîne, sans
        # accents). Sans ça, « pelouse sèche » ne trouvait pas « Pelouses sèches »
        # (l'espace coupait la sous-chaîne au mauvais endroit à cause du pluriel).
        words = search.split() or [search]
        with connection.cursor() as cursor:
            text_conds = " AND ".join(
                ["unaccent(search_name) ILIKE unaccent(%s)"] * len(words)
            )
            sql = f"""
                SELECT cd_hab, cd_typo, lb_code, search_name,
                       lb_hab_fr, lb_hab_fr_complet, lb_typo, niveau
                FROM ref_habitats.autocomplete_habitat
                WHERE (({text_conds})
            """
            params = [f'%{w}%' for w in words]

            if is_numeric:
                sql += " OR cd_hab::text LIKE %s"
                params.append(f'{search}%')

            sql += ")"

            cd_typo = request.query_params.get('cd_typo')
            if cd_typo:
                sql += " AND cd_typo = %s"
                params.append(int(cd_typo))

            sql += """
                ORDER BY
                    CASE
                        WHEN cd_hab::text = %s THEN 0
                        WHEN lower(lb_code) = lower(%s) THEN 1
                        ELSE 2
                    END,
                    similarity(unaccent(search_name), unaccent(%s)) DESC
                LIMIT %s
            """
            params.extend([search, search, search, limit])

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
        """
        Classification d'origine d'un habitat + habitats liés (HabRef). #89

        Réponse : {
          "habitat": { cd_hab, lb_code, lb_typo, lb_hab_fr, lb_hab_fr_complet, niveau },
          "related": [ { cd_hab_entre, cd_typo_entre, lb_typo, lb_code_entre, lb_hab_entre, ... } ]
        }

        Permet à la puce d'afficher la classification d'origine et les habitats
        liés à partir du seul cd_hab — indépendamment de ce qui est stocké côté
        enjeu/action (factorisation : même rendu partout).

        NB : `habref_corresp_hab` ne contient que des relations intra-référentiel
        (sous-types/associés), pas de table de correspondance entre référentiels.
        """
        from django.db import connection
        with connection.cursor() as cur:
            # Classification d'origine (depuis la table d'autocomplete dénormalisée)
            cur.execute(
                """
                SELECT cd_hab, lb_code, lb_typo, lb_hab_fr, lb_hab_fr_complet, niveau
                FROM ref_habitats.autocomplete_habitat
                WHERE cd_hab = %s
                LIMIT 1
                """,
                [cd_hab],
            )
            row = cur.fetchone()
            habitat = None
            if row:
                hcols = ['cd_hab', 'lb_code', 'lb_typo', 'lb_hab_fr', 'lb_hab_fr_complet', 'niveau']
                habitat = dict(zip(hcols, row))
                if habitat.get('lb_typo'):
                    habitat['lb_typo'] = habitat['lb_typo'].replace('_', ' ')

            # Habitats liés (même référentiel) : code + nom résolus via habref.
            cur.execute(
                """
                SELECT c.id, c.cd_hab, c.cd_hab_entre, c.cd_typo_entre,
                       t.lb_typo,
                       COALESCE(NULLIF(c.lb_code_entre, ''), h.lb_code) AS lb_code_entre,
                       COALESCE(NULLIF(c.lb_hab_entre, ''), h.lb_hab_fr) AS lb_hab_entre,
                       c.niveau_entre, c.type_rel
                FROM ref_habitats.habref_corresp_hab c
                JOIN ref_habitats.typoref t ON t.cd_typo = c.cd_typo_entre
                LEFT JOIN ref_habitats.habref h ON h.cd_hab = c.cd_hab_entre
                WHERE c.cd_hab = %s
                ORDER BY c.cd_typo_entre, c.cd_hab_entre
                """,
                [cd_hab],
            )
            cols = [d[0] for d in cur.description]
            related = [dict(zip(cols, r)) for r in cur.fetchall()]
        return Response({'habitat': habitat, 'related': related})

    @action(detail=False, methods=['post'], url_path='validate-bulk')
    def validate_bulk(self, request):
        """
        Valide une liste d'entrées (codes cd_hab, codes nomenclature lb_code,
        ou noms français) contre le référentiel HabRef.

        Auto-détection du format :
        - Entrée numérique → recherche par cd_hab (exact)
        - Entrée texte type code (ex: "G1.6", "E1.2") → recherche par lb_code
        - Entrée texte libre → recherche par nom français (lb_hab_fr)

        POST body: {"items": ["16265", "G1.6", "Hêtraies acidiphiles", ...]}
        Returns: {
            "found": [{"input": "...", "cd_hab": ..., "lb_hab_fr": ..., ...}],
            "not_found": [{"input": "...", "candidates": [...]}],
        }
        """
        items = request.data.get('items', [])
        if not items:
            return Response({'found': [], 'not_found': []})

        found = []
        not_found = []
        already_found_cd_habs = set()

        result_fields = (
            'cd_hab', 'lb_hab_fr', 'lb_hab_fr_complet',
            'cd_typo', 'lb_code', 'niveau',
        )

        for item in items:
            raw = str(item).strip()
            if not raw:
                continue

            match = None

            # 1) Numérique → cd_hab
            try:
                code_int = int(raw)
                match = Habref.objects.filter(cd_hab=code_int).values(
                    *result_fields
                ).first()
            except (ValueError, TypeError):
                pass

            # 2) Recherche par lb_code (codes EUNIS, Corine Biotope, etc.)
            if not match:
                match = Habref.objects.filter(
                    lb_code__iexact=raw
                ).values(*result_fields).first()

            # 3) Recherche par nom français (exact puis partiel)
            if not match:
                match = Habref.objects.filter(
                    Q(lb_hab_fr__iexact=raw)
                    | Q(lb_hab_fr_complet__iexact=raw)
                ).values(*result_fields).first()

            if not match:
                match = Habref.objects.filter(
                    Q(lb_hab_fr__icontains=raw)
                    | Q(lb_hab_fr_complet__icontains=raw)
                ).values(*result_fields).first()

            if match and match['cd_hab'] not in already_found_cd_habs:
                entry = dict(match)
                entry['input'] = raw
                found.append(entry)
                already_found_cd_habs.add(match['cd_hab'])
            elif not match:
                # Proposer des candidats proches (trigrammes)
                candidates = []
                try:
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT cd_hab, lb_hab_fr, lb_code
                            FROM ref_habitats.autocomplete_habitat
                            WHERE unaccent(search_name) ILIKE unaccent(%s)
                            ORDER BY similarity(unaccent(search_name), unaccent(%s)) DESC
                            LIMIT 3
                        """, [f'%{raw}%', raw])
                        for row in cursor.fetchall():
                            candidates.append({
                                'cd_hab': row[0],
                                'lb_hab_fr': row[1],
                                'lb_code': row[2],
                            })
                except Exception:
                    pass
                not_found.append({'input': raw, 'candidates': candidates})

        return Response({'found': found, 'not_found': not_found})
