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

from django.db.models import Count, Max
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from .federation import PeutLire
from .filters import (
    annoter_correspondances, filtrer_contenus, filtrer_plans, liste,
    trier_contenus, trier_plans,
)
from .identites import identites
from .models import ContenuIndexe, PlanIndexe
from .pagination import ExplorationPagination
from .serializers import (
    ContenuResultatSerializer, PlanResultatSerializer, contexte_provenance,
)


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

        # #650 — Dire quel champ a répondu. Posé APRÈS les compteurs : ces
        # annotations entreraient sinon dans leur `GROUP BY` et fausseraient les
        # totaux affichés au-dessus de la liste.
        resultats = annoter_correspondances(
            resultats, request.query_params, info.get('approximatif', False)
        )

        paginateur = ExplorationPagination()
        page = paginateur.paginate_queryset(resultats, request, view=self)
        donnees = ContenuResultatSerializer(
            page, many=True, context=contexte_provenance(page),
        ).data

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
            PlanResultatSerializer(
                page, many=True, context=contexte_provenance(page),
            ).data
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
        identite = identites({plan.instance_id}).get(plan.instance_id, {})
        return Response({
            **(plan.fiche or {}),
            'reference': reference,
            'instance_id': plan.instance_id,
            # Le nom de la structure d'origine, et pas seulement son
            # identifiant : c'est la seule chose qui, sur une fiche ouverte
            # depuis une liste de résultats, dise qui a rédigé ce plan.
            'instance_libelle': identite.get('libelle') or plan.instance_id,
            'url_instance': plan.url_instance or identite.get('url_publique', ''),
            # La date dit à l'appelant l'âge de ce qu'il affiche. Un instantané
            # sans date ne se distingue pas d'une donnée jointe à la volée, et
            # c'est précisément la différence qu'il faut pouvoir voir.
            'date_publication': plan.date_publication,
        })


class InstancesExplorationView(APIView):
    """
    Les structures dont les données alimentent cette recherche.

    Sert deux besoins de l'interface, et un seul appel les couvre :

    - **nommer la provenance** — le filtre « structure d'origine » a besoin des
      libellés, que les tuiles portent déjà mais qu'il faut connaître avant
      d'avoir cherché quoi que ce soit ;
    - **dire ce que couvre l'exploration** — « 4 structures, 312 plans » répond
      à la question qu'un résultat manquant fait toujours poser : est-ce que ce
      plan n'existe pas, ou est-ce que sa structure ne publie pas ?

    Seules les instances **présentes dans l'index** figurent ici. Une instance
    enrôlée mais qui n'a encore rien déposé ne filtre rien et ne couvre rien :
    l'afficher promettrait des résultats que la recherche ne rendra jamais.
    """

    permission_classes = [PeutLire]

    def get(self, request):
        volumes = {
            ligne['instance_id']: ligne
            for ligne in PlanIndexe.objects.values('instance_id').annotate(
                plans=Count('id'), derniere_publication=Max('date_publication'),
            )
        }
        contenus = dict(
            ContenuIndexe.objects.values_list('instance_id')
            .annotate(n=Count('id')).values_list('instance_id', 'n')
        )
        connues = identites(set(volumes))

        instances = [
            {
                'instance_id': instance_id,
                'libelle': connues.get(instance_id, {}).get('libelle') or instance_id,
                'url_publique': connues.get(instance_id, {}).get('url_publique', ''),
                'plans': ligne['plans'],
                'contenus': contenus.get(instance_id, 0),
                'derniere_publication': ligne['derniere_publication'],
            }
            for instance_id, ligne in volumes.items()
        ]
        # Par nom : c'est ainsi que la liste sera lue dans un filtre.
        instances.sort(key=lambda i: i['libelle'].lower())

        return Response({'count': len(instances), 'instances': instances})
