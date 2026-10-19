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
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
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
from . import schema
from .serializers import (
    ContenuResultatSerializer, PlanResultatSerializer, identite_locale, prefetch_sites,
)
from .serializers_fiche import FichePubliqueSerializer


#: Le prefetch vit dans `serializers` : la publication vers le hub en a le même
#: besoin, et le dupliquer ferait diverger les deux chemins en silence.
_prefetch_sites = prefetch_sites


class ExplorationContenuViewSet(ViewSet):
    """Recherche dans le contenu des plans de gestion."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id='exploration_contenus_list',
        summary="Rechercher dans le contenu des plans",
        description=(
            "Objets explorables (enjeux, facteurs d'influence, pressions, objectifs, "
            "indicateurs, actions) des plans validés, modifiés ou archivés de **toutes** "
            "les structures — jamais un brouillon, jamais de budget, RH ni mesures.\n\n"
            "`compteurs` donne le nombre de résultats par type pour la recherche "
            "entière, indépendamment de `onglet`. Chaque résultat dit quels champs ont "
            "répondu (`correspondances`), en donne un extrait, et porte le bandeau de "
            "son plan. `acces_direct` vrai = le plan existe dans cette base et ses "
            "écrans réels s'ouvrent ; faux = seule la fiche publique est consultable.\n\n"
            "Quand l'instance explore via le hub (`CICADA_EXPLORATION_SOURCE=hub`), la "
            "requête est relayée telle quelle et la réponse a la même forme."
        ),
        parameters=schema.PARAMS_CONTENUS,
        responses={
            200: schema.REPONSE_CONTENUS,
            401: schema.REPONSE_401,
            502: schema.REPONSE_502,
        },
        tags=[schema.TAG_EXPLORATION],
    )
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
        donnees = ContenuResultatSerializer(page, many=True, context={
            'mot_cle': request.query_params.get('q', ''),
            'approximatif': info.get('approximatif', False),
        }).data

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

    @extend_schema(
        operation_id='exploration_federation_documents_list',
        summary="Lire l'index local, pour une exploration centralisée",
        description=(
            "Pages de documents d'index **produits par cette instance** (jamais "
            "ceux reçus d'ailleurs), identifiants locaux remplacés par des codes "
            "nationaux (INSEE, INPN). Machine à machine : authentification par "
            "jeton partagé, pas par compte utilisateur. Pages de 500 documents "
            "(2000 au plus). `format_version` dit comment lire les documents."
        ),
        parameters=[
            schema.PARAM_JETON_FEDERATION,
            schema.PARAM_PAGE,
            OpenApiParameter(
                'page_size', OpenApiTypes.INT, OpenApiParameter.QUERY,
                description="Taille de page (500 par défaut, 2000 au plus).",
            ),
        ],
        responses={
            200: schema.REPONSE_FEDERATION_DOCUMENTS,
            403: schema.REPONSE_403_FEDERATION,
        },
        tags=[schema.TAG_FEDERATION],
    )
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

    @extend_schema(
        operation_id='exploration_plans_retrieve',
        summary="Fiche publique d'un plan de gestion",
        description=(
            "Structure complète du plan en lecture seule : enjeux, facteurs, pressions, "
            "objectifs, niveaux d'exigence, résultats attendus, indicateurs, métriques "
            "et actions avec leur suivi et leurs protocoles. **Jamais** de budget, RH, "
            "mesures ni réalisations (`serializers_fiche`). Le plan doit être validé, "
            "modifié ou archivé : un brouillon répond 404.\n\n"
            "En exploration relayée, `slug` peut être une référence `instance:slug` "
            "(ex. `rnf:camargue`) ; la fiche est alors l'instantané déposé sur le hub."
        ),
        parameters=[OpenApiParameter(
            'slug', OpenApiTypes.STR, OpenApiParameter.PATH,
            description="Slug du plan, ou référence `instance:slug` en exploration "
                        "relayée.",
        )],
        responses={
            200: FichePubliqueSerializer,
            401: schema.REPONSE_401,
            404: schema.REPONSE_404,
            502: schema.REPONSE_502,
        },
        tags=[schema.TAG_EXPLORATION],
    )
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

        # #703 — une référence « instance:slug » ouverte en exploration locale
        # (lien produit sur l'exploration nationale, partagé). Celle de cette
        # instance désigne l'un de ses plans ; celle d'une autre structure n'a
        # pas de fiche ici, et ouvrir l'homonyme local serait une réponse fausse
        # et silencieuse.
        if ':' in slug:
            instance, slug = slug.split(':', 1)
            if instance != settings.CICADA_INSTANCE_ID:
                return Response({
                    'erreur': 'autre_structure',
                    'instance_id': instance,
                    'detail': (
                        "Ce plan appartient à une autre structure : sa fiche n'est "
                        "consultable que depuis l'exploration nationale."
                    ),
                }, status=404)

        plan = get_object_or_404(
            PlanGestion.objects.filter(statut__in=INDEXED_STATUSES)
            .select_related('id_type_document')
            .prefetch_related(_prefetch_sites()),
            slug=slug,
        )
        # #692 — même provenance que la fiche servie par le hub. Pas de date de
        # publication : c'est une lecture en direct de cette base, pas un
        # instantané déposé.
        return Response({
            **FichePubliqueSerializer(construire_fiche(plan)).data,
            **identite_locale(),
            'date_publication': None,
        })

    @extend_schema(
        operation_id='exploration_plans_list',
        summary="Rechercher un plan de gestion",
        description=(
            "Plans validés, modifiés ou archivés de toutes les structures, cherchés "
            "par nom de plan, de site, de département ou de région. Mêmes facettes "
            "que la recherche de contenu. `zones_correspondantes` liste les zones "
            "dont le nom porte le mot cherché, pour expliquer un résultat.\n\n"
            "Relayée vers le hub quand l'exploration est nationale ; même forme de "
            "réponse."
        ),
        parameters=schema.PARAMS_PLANS,
        responses={
            200: schema.REPONSE_PLANS,
            401: schema.REPONSE_401,
            502: schema.REPONSE_502,
        },
        tags=[schema.TAG_EXPLORATION],
    )
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
        donnees = PlanResultatSerializer(page, many=True, context={
            'mot_cle': request.query_params.get('q', ''),
        }).data
        return paginateur.get_paginated_response(donnees)


class InstancesExplorationView(APIView):
    """
    Les structures dont les données alimentent cette recherche (#636).

    Même forme de réponse dans les deux modes — relayée par le hub, ou décrivant
    cette seule instance —, pour que l'interface n'ait pas à savoir laquelle des
    deux la sert : c'est la règle depuis le début du relais, et la seule raison
    pour laquelle la bascule d'un mode à l'autre est un réglage et non un
    chantier.

    En local, la réponse ne compte qu'une structure : la sienne. Ce n'est pas un
    cas dégénéré à masquer, c'est l'information exacte — une exploration locale
    ne porte que sur les plans de cette instance, et le dire ici permet à
    l'interface de le montrer plutôt que de laisser conclure à un manque.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id='exploration_instances_list',
        summary="Structures qui alimentent l'exploration",
        description=(
            "Liste des instances présentes dans l'index interrogé, avec leur libellé, "
            "leur URL publique et leurs volumes. En exploration locale, une seule "
            "entrée : cette instance. Via le hub, uniquement les instances ayant "
            "déjà publié. Alimente le filtre « Structure d'origine » et la portée "
            "annoncée avant la recherche."
        ),
        responses={
            200: schema.REPONSE_INSTANCES,
            401: schema.REPONSE_401,
            502: schema.REPONSE_502,
        },
        tags=[schema.TAG_EXPLORATION],
    )
    def get(self, request):
        if relais_actif():
            return relayer('/api/exploration/instances/')

        return Response({
            'count': 1,
            'instances': [{
                'instance_id': settings.CICADA_INSTANCE_ID,
                # #692 — jamais vide, comme la provenance des résultats.
                'libelle': identite_locale()['instance_libelle'],
                'url_publique': settings.CICADA_PUBLIC_URL,
                'plans': PlanGestion.objects.filter(
                    statut__in=INDEXED_STATUSES
                ).count(),
                'contenus': ContenuIndexe.objects.filter(
                    instance_id=settings.CICADA_INSTANCE_ID
                ).count(),
                'derniere_publication': None,
            }],
        })
