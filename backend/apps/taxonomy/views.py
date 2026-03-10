"""Vues API pour le référentiel TaxRef."""

from django.db import models
from django.db.models import Q, F
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Taxref, VMTaxrefListForAutocomplete, TMetaTaxref
from .serializers import (
    TaxrefListSerializer,
    TaxrefDetailSerializer,
    TaxrefAutocompleteSerializer,
    TaxrefVersionSerializer,
)


class TaxrefViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API pour le référentiel taxonomique TaxRef.

    GET /api/taxref/             — liste paginée avec filtres
    GET /api/taxref/<cd_nom>/    — détail d'un taxon
    GET /api/taxref/autocomplete/?search=<terme>&limit=20
    GET /api/taxref/version/     — version courante
    GET /api/taxref/search/<field>/<ilike>/  — recherche libre
    """

    permission_classes = [IsAuthenticated]
    lookup_field = 'cd_nom'

    def get_queryset(self):
        qs = Taxref.objects.all()

        # Filtres
        cd_nom = self.request.query_params.get('cd_nom')
        if cd_nom:
            qs = qs.filter(cd_nom=cd_nom)

        regne = self.request.query_params.get('regne')
        if regne:
            qs = qs.filter(regne__iexact=regne)

        group2_inpn = self.request.query_params.get('group2_inpn')
        if group2_inpn:
            qs = qs.filter(group2_inpn__iexact=group2_inpn)

        id_rang = self.request.query_params.get('id_rang')
        if id_rang:
            qs = qs.filter(id_rang=id_rang)

        # rank_limit : ne garder que les rangs >= au rang donné
        rank_limit = self.request.query_params.get('rank_limit')
        if rank_limit:
            qs = qs.filter(id_rang=rank_limit)

        # Filtrer uniquement les noms valides (cd_nom == cd_ref)
        valid_only = self.request.query_params.get('valid_only')
        if valid_only and valid_only.lower() in ('true', '1'):
            qs = qs.filter(cd_nom=F('cd_ref'))

        return qs.order_by('cd_nom')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TaxrefDetailSerializer
        return TaxrefListSerializer

    @action(detail=False, methods=['get'])
    def version(self, request):
        """Retourne la version courante du référentiel TaxRef."""
        meta = TMetaTaxref.objects.filter(
            referential_name='taxref'
        ).order_by('-update_date').first()
        if not meta:
            return Response(
                {'detail': 'Aucune version de TaxRef installée.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(TaxrefVersionSerializer(meta).data)

    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """
        Autocomplete sur les taxons via trigrammes + unaccent.

        Paramètres :
        - search : terme de recherche (min 2 caractères)
        - limit : nombre max de résultats (défaut 20)
        - regne : filtre optionnel par règne
        - group2_inpn : filtre optionnel par groupe
        """
        search = request.query_params.get('search', '').strip()
        if len(search) < 2:
            return Response([])

        limit = min(int(request.query_params.get('limit', 20)), 100)

        from django.db import connection
        with connection.cursor() as cursor:
            # Requête avec similarity() + unaccent() pour la pertinence
            sql = """
                SELECT cd_nom, cd_ref, search_name, nom_valide,
                       nom_vern, lb_nom, regne, group2_inpn, id_rang
                FROM taxonomie.vm_taxref_list_forautocomplete
                WHERE unaccent(search_name) ILIKE unaccent(%s)
            """
            params = [f'%{search}%']

            # Filtres optionnels
            regne = request.query_params.get('regne')
            if regne:
                sql += " AND regne = %s"
                params.append(regne)

            group2_inpn = request.query_params.get('group2_inpn')
            if group2_inpn:
                sql += " AND group2_inpn = %s"
                params.append(group2_inpn)

            sql += """
                ORDER BY similarity(unaccent(search_name), unaccent(%s)) DESC
                LIMIT %s
            """
            params.extend([search, limit])

            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return Response(results)

    @action(
        detail=False,
        methods=['get'],
        url_path='search/(?P<field>[a-z_]+)/(?P<ilike>.+)',
    )
    def search_field(self, request, field=None, ilike=None):
        """
        Recherche libre sur un champ donné du TaxRef.

        GET /api/taxref/search/nom_vern/renard/
        """
        allowed_fields = [
            'lb_nom', 'nom_complet', 'nom_valide', 'nom_vern',
            'nom_vern_eng', 'groupe2_inpn', 'famille', 'ordre', 'classe',
        ]
        if field not in allowed_fields:
            return Response(
                {'detail': f"Champ '{field}' non autorisé. "
                           f"Champs autorisés : {', '.join(allowed_fields)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        limit = min(int(request.query_params.get('limit', 20)), 100)
        qs = Taxref.objects.filter(
            **{f'{field}__icontains': ilike}
        ).order_by('cd_nom')[:limit]

        return Response(TaxrefListSerializer(qs, many=True).data)
