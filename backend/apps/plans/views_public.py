"""
API publique des métadonnées des plans de gestion (#645).

Servie par **l'instance**, et non par le hub d'exploration : le hub ne stocke
que l'index de recherche et la fiche publique d'un plan (#636), ni les
rédacteurs, ni les dates de validation, ni l'identifiant Doc'Gestion. Les
exposer depuis le hub demanderait d'élargir le contrat de publication et de
dépendre du consentement de chaque structure, là où le besoin — relier une GED
aux plans d'une instance donnée — est local par nature.

Ouverte : ni authentification, ni jeton. Les métadonnées d'un plan de gestion
ne sont pas sensibles. Mais l'ouverture reste sous l'interrupteur
`SiteConfiguration.api_publique_plans`, coupé par défaut : une instance qui met
à jour CICADA ne doit pas se mettre à publier sans que personne l'ait décidé.
"""

from datetime import datetime, time

from django.utils.dateparse import parse_date, parse_datetime
from django.utils.timezone import get_current_timezone, is_naive, make_aware
from rest_framework import viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny

from apps.core.models import SiteConfiguration

from .models import PlanGestion
from .serializers_public import PlanPublicSerializer, prefetch_sites_publics

# Les brouillons restent hors du périmètre : ce sont des plans en cours de
# rédaction, dont le nom et la période changent encore. Les publier sur une API
# ouverte reviendrait à diffuser du travail non abouti.
STATUTS_PUBLICS = ('valide', 'modifie', 'archive')


class PlansPublicsPagination(PageNumberPagination):
    """
    Pagination pilotée par l'appelant.

    Une GED qui rattrape son retard veut de grosses pages ; une sonde de
    supervision, une petite. Le plafond existe pour qu'une page ne puisse pas
    devenir un export complet déguisé.
    """

    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class PlanPublicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Métadonnées des plans de gestion, en lecture seule et sans authentification.

    - `GET /api/public/plans/` — liste paginée
    - `GET /api/public/plans/{uuid}/` — un plan par son identifiant stable

    Filtres : `modifie_depuis` (date ou datetime ISO), `statut`, `id_inpn`
    (code INPN d'un site rattaché), `rang`.
    """

    serializer_class = PlanPublicSerializer
    permission_classes = [AllowAny]
    # Aucune authentification : sans cette ligne, l'authentification JWT par
    # défaut rejetterait un en-tête `Authorization` mal formé avec un 401,
    # alors que l'appelant n'est pas censé en envoyer.
    authentication_classes = []
    pagination_class = PlansPublicsPagination
    lookup_field = 'uuid_plan'
    lookup_url_kwarg = 'uuid'

    def initial(self, request, *args, **kwargs):
        """Refuse tout dès l'entrée si l'instance n'a pas ouvert son API."""
        configuration = SiteConfiguration.objects.first()
        if not (configuration and configuration.api_publique_plans):
            raise NotFound(
                "L'API publique des plans de gestion n'est pas activée sur "
                "cette instance de CICADA."
            )
        return super().initial(request, *args, **kwargs)

    def get_queryset(self):
        queryset = (
            PlanGestion.objects
            .filter(statut__in=STATUTS_PUBLICS)
            .select_related(
                'id_type_document', 'id_evaluation', 'id_redacteur_type',
                'plan_parent',
            )
            .prefetch_related(prefetch_sites_publics())
            # Ordre croissant, et non l'ordre d'affichage habituel : un
            # rattrapage `modifie_depuis` parcourt les pages pendant que la
            # base continue de vivre. Un plan modifié en cours de parcours part
            # vers la fin de la liste — il sera vu deux fois, ce qu'une reprise
            # par identifiant absorbe. En ordre décroissant, il remonterait
            # avant le curseur et serait purement manqué.
            .order_by('date_maj', 'id_pg')
        )
        return self._appliquer_filtres(queryset)

    def _appliquer_filtres(self, queryset):
        params = self.request.query_params

        depuis = params.get('modifie_depuis')
        if depuis:
            queryset = queryset.filter(date_maj__gte=self._instant(depuis))

        statut = params.get('statut')
        if statut:
            if statut not in STATUTS_PUBLICS:
                raise ValidationError({
                    'statut': (
                        "Statut inconnu ou non exposé. Valeurs acceptées : "
                        f"{', '.join(STATUTS_PUBLICS)}."
                    )
                })
            queryset = queryset.filter(statut=statut)

        id_inpn = params.get('id_inpn')
        if id_inpn:
            queryset = queryset.filter(sites__site__id_inpn=id_inpn)

        rang = params.get('rang')
        if rang:
            if not rang.isdigit():
                raise ValidationError({'rang': "Le rang doit être un entier."})
            queryset = queryset.filter(rang=int(rang))

        return queryset.distinct()

    @staticmethod
    def _instant(valeur):
        """Interprète `modifie_depuis`, en datetime ISO ou en date seule."""
        instant = parse_datetime(valeur)
        if instant is None:
            jour = parse_date(valeur)
            if jour is None:
                raise ValidationError({
                    'modifie_depuis': (
                        "Date illisible. Format attendu : 2026-08-24 ou "
                        "2026-08-24T09:00:00Z."
                    )
                })
            instant = datetime.combine(jour, time.min)
        if is_naive(instant):
            instant = make_aware(instant, get_current_timezone())
        return instant
