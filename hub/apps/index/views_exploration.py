"""
API de lecture de l'exploration.

Deux modes, correspondant au sélecteur de la page d'exploration :

- ``/api/exploration/contenus/`` — rechercher **dans le contenu** des plans ;
- ``/api/exploration/plans/`` — rechercher **un plan de gestion** par son nom,
  celui d'un de ses sites, d'un département ou d'une région, et consulter sa
  fiche.

**C'est ici que se joue le choix d'architecture** : la recherche s'exécute sur
l'index agrégé, en un seul passage. Le tri par pertinence est donc transverse
aux instances, et les compteurs d'onglets exacts — deux choses qu'une fédération
qui interrogerait chaque instance puis fusionnerait les réponses ne peut pas
garantir, faute de scores comparables entre index.

**Périmètre.** Ces vues n'appliquent aucun périmètre utilisateur : le hub ne
connaît pas les utilisateurs. Ce qui borne l'exploration, c'est l'index
lui-même — seuls les plans qu'une instance a jugés explorables y figurent — et
le jeton de lecture, qui n'est délivré qu'aux instances. C'est l'instance qui
relaie qui reste responsable d'authentifier son utilisateur.
"""

from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .federation import PeutLire
from .filters import filtrer_contenus, filtrer_plans, liste, trier_contenus, trier_plans
from .models import ContenuIndexe, PlanIndexe
from .pagination import ExplorationPagination
from .serializers import ContenuResultatSerializer, PlanResultatSerializer


class ExplorationContenuViewSet(ViewSet):
    """Recherche dans le contenu des plans de gestion, toutes instances confondues."""

    permission_classes = [PeutLire]

    def list(self, request):
        # Le bandeau du plan est joint, pas recopié sur chaque ligne : c'est
        # tout l'intérêt d'avoir fait du plan une table (cf. `models`).
        base = ContenuIndexe.objects.select_related('plan')
        # #651 — `info` dit si la recherche a dû se rabattre sur des termes
        # approchants. Sans le signaler, l'utilisateur croit avoir trouvé ce
        # qu'il cherchait alors qu'aucun résultat ne correspond vraiment.
        info = {}
        filtres = filtrer_contenus(base, request.query_params, info)

        # Les compteurs d'onglets sont calculés AVANT le filtre d'onglet, pour
        # qu'ils restent ceux de la recherche entière : sans cela, sélectionner
        # « Pressions » ferait tomber à zéro tous les autres onglets.
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
            approximatif=info.get('approximatif', False),
            compteurs={
                'tout': sum(compteurs.values()),
                **{
                    type_contenu: compteurs.get(type_contenu, 0)
                    for type_contenu, _ in ContenuIndexe.TYPE_CHOICES
                },
            },
        )


class ExplorationPlanViewSet(ViewSet):
    """Recherche d'un plan de gestion, et consultation de sa fiche publiée."""

    permission_classes = [PeutLire]
    lookup_field = 'reference'
    # Une référence est « instance:slug » — le deux-points doit passer.
    lookup_value_regex = '[-\\w]+:[-\\w]+'

    def list(self, request):
        resultats = trier_plans(
            filtrer_plans(PlanIndexe.objects.all(), request.query_params),
            request.query_params,
        )
        paginateur = ExplorationPagination()
        page = paginateur.paginate_queryset(resultats, request, view=self)
        return paginateur.get_paginated_response(
            PlanResultatSerializer(page, many=True).data
        )

    def retrieve(self, request, reference=None):
        """
        Fiche publique d'un plan, resservie telle que son instance l'a publiée.

        Le hub ne reconstruit rien : il ne connaît ni les enjeux ni les actions,
        seulement l'arbre JSON que l'instance a rendu. C'est ce qui permet de
        servir la fiche d'un plan hébergé ailleurs sans répliquer ici le modèle
        métier de CICADA — au prix d'une fiche qui vieillit jusqu'à la
        publication suivante.
        """
        instance_id, _, slug = (reference or '').partition(':')
        plan = get_object_or_404(PlanIndexe, instance_id=instance_id, slug=slug)

        # La fiche est renvoyée **à plat**, exactement comme la sert une
        # instance, et non enveloppée dans un objet. Une enveloppe obligerait le
        # frontend à distinguer les deux sources — ce que la bascule vers le hub
        # doit précisément lui épargner. Les métadonnées de fédération viennent
        # s'ajouter à côté : aucune ne porte le nom d'un champ de fiche.
        return Response({
            **(plan.fiche or {}),
            'reference': reference,
            'instance_id': plan.instance_id,
            'url_instance': plan.url_instance,
            # La date dit à l'appelant l'âge de ce qu'il affiche. Un instantané
            # sans date ne se distingue pas d'une donnée jointe à la volée, et
            # c'est précisément la différence qu'il faut pouvoir voir.
            'date_publication': plan.date_publication,
        })
