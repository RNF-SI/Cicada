"""
API de l'exploration des données.

Deux modes, correspondant au sélecteur de la page d'accueil de l'exploration :

- ``/api/exploration/contenus/`` — rechercher **dans le contenu** des plans
  (enjeux, facteurs d'influence, pressions, objectifs, indicateurs, actions) ;
- ``/api/exploration/plans/`` — rechercher **un plan de gestion** par son nom,
  celui d'un de ses sites, d'un département ou d'une région.

**Périmètre volontairement transverse.** Contrairement au reste de l'API des
plans, ces deux vues n'appliquent **pas** le périmètre de `apps.plans.access`
(#610) : l'exploration est un outil de partage inter-organismes, tout
utilisateur connecté voit les plans de tous les organismes. Ce qui la borne,
c'est l'index lui-même — seuls les plans validés, modifiés ou archivés y
figurent, jamais un brouillon — et les champs exposés, qui ne contiennent ni
budget, ni RH, ni données empiriques.
"""

from django.db.models import Count, Prefetch
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.plans.models import CorSitePg, PlanGestion
from apps.users.models import CorOgSite

from .filters import (
    filtrer_contenus, filtrer_plans, trier_contenus, trier_plans,
)
from .indexing import INDEXED_STATUSES
from .models import ContenuIndexe
from .pagination import ExplorationPagination
from .serializers import ContenuResultatSerializer, PlanResultatSerializer


def _prefetch_sites():
    """
    Prefetch des sites d'un plan, avec leur gestionnaire principal.

    Sans ça, chaque tuile déclencherait une requête par site puis une par
    organisme — soit une cinquantaine de requêtes pour une page de résultats.
    """
    gestionnaires = Prefetch(
        'site__corogsite_set',
        queryset=CorOgSite.objects.filter(principal=True).select_related('uuid_og'),
        to_attr='gestionnaires_principaux',
    )
    return Prefetch(
        'sites',
        queryset=(
            CorSitePg.objects
            .select_related('site')
            .prefetch_related(gestionnaires)
            .order_by('rang', 'site__nom_site')
        ),
        to_attr='sites_ordonnes',
    )


class ExplorationContenuViewSet(ViewSet):
    """Recherche dans le contenu des plans de gestion."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        prefetch = _prefetch_sites()
        base = (
            ContenuIndexe.objects
            .select_related('id_pg', 'id_pg__id_type_document')
            .prefetch_related(
                Prefetch('id_pg__sites', queryset=prefetch.queryset,
                         to_attr='sites_ordonnes')
            )
        )
        filtres = filtrer_contenus(base, request.query_params)

        # Les compteurs d'onglets sont calculés AVANT le filtre d'onglet, pour
        # qu'ils restent ceux de la recherche entière (cf. `filtrer_contenus`).
        compteurs = {
            ligne['type_contenu']: ligne['total']
            for ligne in filtres.values('type_contenu')
            .annotate(total=Count('id')).order_by()
        }

        resultats = filtres
        onglet = request.query_params.get('onglet')
        if onglet and onglet != 'tout':
            resultats = resultats.filter(type_contenu=onglet)
        resultats = trier_contenus(resultats, request.query_params)

        paginateur = ExplorationPagination()
        page = paginateur.paginate_queryset(resultats, request, view=self)
        donnees = ContenuResultatSerializer(page, many=True).data

        return paginateur.get_paginated_response(
            donnees,
            compteurs={
                'tout': sum(compteurs.values()),
                **{
                    type_contenu: compteurs.get(type_contenu, 0)
                    for type_contenu, _ in ContenuIndexe.TYPE_CHOICES
                },
            },
        )


class ExplorationPlanViewSet(ViewSet):
    """Recherche d'un plan de gestion par nom, site, département ou région."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        base = (
            PlanGestion.objects
            .filter(statut__in=INDEXED_STATUSES)
            .select_related('id_type_document')
            .prefetch_related(_prefetch_sites())
        )
        resultats = trier_plans(
            filtrer_plans(base, request.query_params), request.query_params
        )

        paginateur = ExplorationPagination()
        page = paginateur.paginate_queryset(resultats, request, view=self)
        donnees = PlanResultatSerializer(page, many=True).data
        return paginateur.get_paginated_response(donnees)
