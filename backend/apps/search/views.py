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

from apps.plans.models import PlanGestion

from .federation import (
    FORMAT_VERSION, HasFederationToken, _bandeau_du_plan, codes_de_la_page,
    document_publie,
)
from .fiche import construire_fiche
from .filters import (
    annoter_correspondances, filtrer_contenus, filtrer_plans, liste,
    trier_contenus, trier_plans,
)
from .indexing import INDEXED_STATUSES
from .models import ContenuIndexe
from .pagination import ExplorationPagination, FederationPagination
from .relay import reference_plan, relais_actif, relayer
from .serializers import (
    ContenuResultatSerializer, PlanResultatSerializer, prefetch_sites,
)
from .serializers_fiche import FichePubliqueSerializer


#: Le prefetch vit dans `serializers` : la publication vers le hub en a le même
#: besoin, et le dupliquer ferait diverger les deux chemins en silence.
_prefetch_sites = prefetch_sites


class ExplorationContenuViewSet(ViewSet):
    """Recherche dans le contenu des plans de gestion."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        if relais_actif():
            return relayer('/api/exploration/contenus/', request.query_params)

        prefetch = _prefetch_sites()
        base = (
            ContenuIndexe.objects
            .select_related('id_pg', 'id_pg__id_type_document')
            .prefetch_related(
                Prefetch('id_pg__sites', queryset=prefetch.queryset,
                         to_attr='sites_ordonnes')
            )
        )
        # #651 — `info` dit si la recherche a dû se rabattre sur des termes
        # approchants. Sans le signaler, l'utilisateur croit avoir trouvé ce
        # qu'il cherchait alors qu'aucun résultat ne correspond vraiment.
        info = {}
        filtres = filtrer_contenus(base, request.query_params, info)

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

        # #650 — Dire quel champ a répondu. Posé APRÈS les compteurs : ces
        # annotations entreraient sinon dans leur `GROUP BY` et fausseraient les
        # totaux affichés au-dessus de la liste.
        resultats = annoter_correspondances(
            resultats, request.query_params, info.get('approximatif', False)
        )

        paginateur = ExplorationPagination()
        page = paginateur.paginate_queryset(resultats, request, view=self)
        donnees = ContenuResultatSerializer(page, many=True).data

        return paginateur.get_paginated_response(
            donnees,
            approximatif=info.get('approximatif', False),
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

        # Idem pour les codes nationaux des zones et des sites : deux requêtes
        # pour la page, et non deux par document (cf. `codes_de_la_page`).
        codes_zones, codes_sites = codes_de_la_page(page)

        return paginateur.get_paginated_response(
            [
                document_publie(contenu, bandeaux, codes_zones, codes_sites)
                for contenu in page
            ],
            format_version=FORMAT_VERSION,
            instance_id=settings.CICADA_INSTANCE_ID,
            instance_label=settings.CICADA_INSTANCE_LABEL,
        )


class ExplorationPlanViewSet(ViewSet):
    """Recherche d'un plan de gestion, et consultation de sa fiche publique."""

    permission_classes = [IsAuthenticated]
    lookup_field = 'slug'
    # Le deux-points est admis pour laisser passer une référence « instance:slug »
    # quand l'exploration est relayée vers le hub (cf. `relay.reference_plan`).
    lookup_value_regex = '[-\\w:]+'

    def retrieve(self, request, slug=None):
        """
        Fiche publique en lecture seule d'un plan de gestion.

        Le plan doit être validé, modifié ou archivé : un brouillon n'est pas
        explorable, donc pas consultable ici. Le contenu exposé est strictement
        celui de `serializers_fiche` — structure du plan, sans budget, RH,
        mesures ni réalisations.
        """
        if relais_actif():
            return relayer(f'/api/exploration/plans/{reference_plan(slug)}/')

        plan = get_object_or_404(
            PlanGestion.objects.filter(statut__in=INDEXED_STATUSES)
            .select_related('id_type_document')
            .prefetch_related(_prefetch_sites()),
            slug=slug,
        )
        return Response(FichePubliqueSerializer(construire_fiche(plan)).data)

    def list(self, request):
        if relais_actif():
            return relayer('/api/exploration/plans/', request.query_params)

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
