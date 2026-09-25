"""
API de dépôt de l'index par les instances (#636).

Trois points d'entrée, qui matérialisent les trois temps d'une publication.
Voir ``federation.py`` pour le raisonnement derrière ce découpage.
"""

import logging

from django.conf import settings

from django.db import transaction
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from .federation import (
    EstFedere, EstInstanceAutorisee, basculer, ingerer_plan,
)
from .identites import identites
from .models import ContenuIndexe, Instance, LotPublication, PlanIndexe
from .serializers_federation import OuvertureLotSerializer, PagePlansSerializer

logger = logging.getLogger(__name__)


class LotPublicationViewSet(ViewSet):
    """Dépôt de l'index d'une instance, en trois temps."""

    permission_classes = [EstInstanceAutorisee]
    lookup_field = 'pk'

    def _lot_ouvert(self, request, pk):
        """
        Récupère un lot ouvert **appartenant à l'appelant**.

        Le filtre sur `instance_id` n'est pas une précaution de forme : sans
        lui, le porteur d'un jeton valide pourrait alimenter puis basculer le
        lot d'une autre instance, c'est-à-dire purger son index.
        """
        return get_object_or_404(
            LotPublication,
            pk=pk,
            instance_id=request.instance_id,
            etat=LotPublication.ETAT_OUVERT,
        )

    def create(self, request):
        """Ouvre un lot pour l'instance porteuse du jeton."""
        serializer = OuvertureLotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        lot = LotPublication.objects.create(
            instance_id=request.instance_id,
            format_version=serializer.validated_data['format_version'],
            # Identité d'affichage, telle que l'instance se nomme aujourd'hui.
            # Portée par le lot et non par le registre : une instance qui publie
            # encore par jeton d'environnement n'a pas de ligne au registre, et
            # lui en créer une ici la ferait basculer du côté « enrôlée » — donc
            # ferait refuser son propre jeton (cf. `identifier_porteur`).
            libelle_declare=serializer.validated_data['libelle'],
            url_publique_declaree=serializer.validated_data['url_publique'],
        )
        logger.info("Lot %s ouvert par l'instance %s.", lot.id, lot.instance_id)
        return Response(
            {
                'lot_id': str(lot.id),
                'instance_id': lot.instance_id,
                'format_version': lot.format_version,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='plans')
    def deposer_plans(self, request, pk=None):
        """
        Dépose une page de plans dans un lot ouvert.

        Chaque page est ingérée dans sa propre transaction : une page qui échoue
        n'annule pas les précédentes, et l'émetteur peut la rejouer. Rien n'est
        visible avant la bascule de toute façon — au sens où rien n'est purgé.
        """
        lot = self._lot_ouvert(request, pk)

        serializer = PagePlansSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plans = serializer.validated_data['plans']

        contenus = 0
        with transaction.atomic():
            for charge in plans:
                contenus += ingerer_plan(charge, lot.instance_id, lot)

            # `F()` plutôt qu'une lecture puis une écriture : deux pages peuvent
            # être envoyées en parallèle par un émetteur pressé.
            from django.db.models import F
            LotPublication.objects.filter(pk=lot.pk).update(
                plans_recus=F('plans_recus') + len(plans),
                contenus_recus=F('contenus_recus') + contenus,
            )

        return Response({'plans_recus': len(plans), 'contenus_recus': contenus})

    @action(detail=True, methods=['post'], url_path='bascule')
    def bascule(self, request, pk=None):
        """Publie le lot et purge les plans de cette instance qui n'y figurent pas."""
        lot = self._lot_ouvert(request, pk)

        with transaction.atomic():
            lot.refresh_from_db()
            purges = basculer(lot)

        return Response({
            'lot_id': str(lot.id),
            'instance_id': lot.instance_id,
            'plans_recus': lot.plans_recus,
            'contenus_recus': lot.contenus_recus,
            'plans_purges': purges,
        })

    def destroy(self, request, pk=None):
        """
        Abandonne un lot ouvert.

        Utile quand l'émetteur détecte lui-même que sa publication est
        incomplète : mieux vaut abandonner que basculer un état partiel, qui
        purgerait du contenu encore valide.
        """
        lot = self._lot_ouvert(request, pk)
        # Abandonner **n'annule pas** ce qui a déjà été écrit : les plans reçus
        # dans ce lot restent à jour de ce que l'émetteur venait d'envoyer. Ce
        # que l'abandon empêche, c'est la purge — donc la disparition de tout ce
        # qui n'avait pas encore été transmis. C'est le bon compromis : la
        # donnée déjà reçue est fraîche, seule la vue d'ensemble est incomplète,
        # et la publication suivante fait de toute façon autorité sur l'état
        # entier de l'instance.
        lot.delete()
        logger.info("Lot %s abandonné par l'instance %s.", pk, request.instance_id)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegistreDesInstances(APIView):
    """
    Qui participe à la fédération, et où en est chacun.

    ## Pourquoi cette vue existe

    Les informations qu'elle rend étaient déjà toutes en base — le registre pour
    l'identité, ``LotPublication`` pour l'historique des dépôts, l'index pour
    les volumes — mais réparties dans trois tables qu'il fallait interroger en
    SQL sur le serveur du hub. Or la question « untel publie-t-il encore ? » se
    pose depuis l'extérieur, souvent dans l'urgence, et sans accès à la base.

    ## Ce qu'elle ne rend pas

    Ni jeton, ni empreinte. Une empreinte SHA-256 d'un jeton de 256 bits n'est
    pas inversible, mais elle permettrait de **vérifier** un jeton deviné hors
    ligne, sans que le hub ne journalise rien.

    ## Instances non enrôlées

    Une instance qui publie via un jeton d'environnement n'a pas de ligne dans
    le registre. Elle figure quand même ici, marquée ``enrolee: false`` : c'est
    précisément la liste de ce qu'il reste à enrôler, et l'omettre donnerait
    d'un hub à moitié migré l'image d'un hub vide.
    """

    permission_classes = [EstFedere]

    def get(self, request):
        plans = dict(
            PlanIndexe.objects.values_list('instance_id')
            .annotate(n=Count('id')).values_list('instance_id', 'n')
        )
        contenus = dict(
            ContenuIndexe.objects.values_list('instance_id')
            .annotate(n=Count('id')).values_list('instance_id', 'n')
        )
        # Dernière bascule *réussie* : un lot ouvert et jamais basculé n'a rien
        # publié, l'afficher ferait passer une publication avortée pour un
        # succès.
        derniers = dict(
            LotPublication.objects
            .filter(etat=LotPublication.ETAT_BASCULE)
            .values_list('instance_id')
            .annotate(d=Max('date_bascule'))
            .values_list('instance_id', 'd')
        )
        enrolees = {i.instance_id: i for i in Instance.objects.all()}

        identifiants = sorted(
            set(enrolees) | set(plans) | set(derniers)
        )
        # Nom et URL résolus par la même cascade que l'exploration : registre,
        # puis ce que l'instance a déclaré en publiant, puis l'identifiant. Deux
        # résolutions séparées finiraient par nommer différemment la même
        # structure selon l'écran.
        connues = identites(identifiants)
        instances = []
        for identifiant in identifiants:
            enrolee = enrolees.get(identifiant)
            derniere = derniers.get(identifiant)
            instances.append({
                'instance_id': identifiant,
                'libelle': connues.get(identifiant, {}).get('libelle') or identifiant,
                'url_publique': connues.get(identifiant, {}).get('url_publique', ''),
                'enrolee': enrolee is not None,
                'active': enrolee.active if enrolee else True,
                'date_enrolement': enrolee.date_enrolement if enrolee else None,
                'derniere_publication': derniere,
                'plans_publies': plans.get(identifiant, 0),
                'contenus_publies': contenus.get(identifiant, 0),
            })

        return Response({
            'hub': settings.HUB_INSTANCE_ID,
            'count': len(instances),
            'instances': instances,
        })
