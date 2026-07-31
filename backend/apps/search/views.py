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

from django.conf import settings
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.plans.models import CorSitePg, PlanGestion
from apps.users.models import CorOgSite

from .federation import (
    FORMAT_VERSION, HasFederationToken, _bandeau_du_plan, document_publie,
)
from .fiche import construire_fiche
from .filters import (
    filtrer_contenus, filtrer_plans, liste, trier_contenus, trier_plans,
)
from .indexing import INDEXED_STATUSES
from .models import ContenuIndexe
from .pagination import ExplorationPagination, FederationPagination
from .serializers import ContenuResultatSerializer, PlanResultatSerializer
from .serializers_fiche import FichePubliqueSerializer


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

        # L'onglet peut couvrir plusieurs types : la maquette n'affiche qu'un
        # onglet « Objectifs » pour les objectifs à long terme et opérationnels.
        resultats = filtres
        onglet = [
            type_contenu for type_contenu in liste(request.query_params, 'onglet')
            if type_contenu != 'tout'
        ]
        if onglet:
            resultats = resultats.filter(type_contenu__in=onglet)
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


class FederationDocumentViewSet(ViewSet):
    """
    Publication de l'index local vers une exploration centralisée (#636).

    Ne publie que les documents **produits ici** : un portail qui a ingéré des
    documents d'autres instances ne les repropage pas. La fédération est en
    étoile, pas en cascade — une topologie transitive rendrait impossible de
    savoir quelle instance fait autorité sur un document, et donc de le retirer.
    """

    permission_classes = [HasFederationToken]

    def list(self, request):
        documents = (
            ContenuIndexe.objects
            .filter(instance_id=settings.CICADA_INSTANCE_ID)
            .order_by('id')
        )

        paginateur = FederationPagination()
        page = paginateur.paginate_queryset(documents, request, view=self)

        # Le bandeau d'affichage est joint ici, une fois pour la page entière :
        # côté portail le plan n'existera pas, il faut donc l'emporter avec le
        # document (cf. `federation._bandeau_du_plan`).
        plans = (
            PlanGestion.objects
            .filter(pk__in={contenu.id_pg_id for contenu in page})
            .select_related('id_type_document')
            .prefetch_related(_prefetch_sites())
        )
        bandeaux = {plan.pk: _bandeau_du_plan(plan) for plan in plans}

        return paginateur.get_paginated_response(
            [document_publie(contenu, bandeaux) for contenu in page],
            format_version=FORMAT_VERSION,
            instance_id=settings.CICADA_INSTANCE_ID,
            instance_label=settings.CICADA_INSTANCE_LABEL,
        )


class ExplorationPlanViewSet(ViewSet):
    """Recherche d'un plan de gestion, et consultation de sa fiche publique."""

    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'
    lookup_value_regex = '[-\\w]+'

    def retrieve(self, request, slug=None):
        """
        Fiche publique en lecture seule d'un plan de gestion.

        Le plan doit être validé, modifié ou archivé : un brouillon n'est pas
        explorable, donc pas consultable ici. Le contenu exposé est strictement
        celui de `serializers_fiche` — structure du plan, sans budget, RH,
        mesures ni réalisations.
        """
        plan = get_object_or_404(
            PlanGestion.objects.filter(statut__in=INDEXED_STATUSES)
            .select_related('id_type_document')
            .prefetch_related(_prefetch_sites()),
            slug=slug,
        )
        return Response(FichePubliqueSerializer(construire_fiche(plan)).data)

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
