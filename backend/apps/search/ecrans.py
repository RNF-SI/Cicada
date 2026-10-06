"""
Instantanés des écrans réels d'un plan, pour les plans distants (#683, #693).

Un plan d'une autre instance n'a pas de données ici : le hub ne stocke que
ce que l'instance émettrice a publié. Pour que ce plan s'ouvre dans les
**mêmes écrans** qu'un plan local — page du plan, arborescence, fiche action
— l'instance publie, avec son index, les réponses d'API que ces écrans
consomment : exactement celles qu'un lecteur d'exploration recevrait en
local, **élaguées par `elaguer()`** des mêmes clés sensibles.

Les constructeurs de réponses sont ceux des vues (`payload_enjeux_du_plan`,
`payload_operations_du_plan`, sérialiseurs de détail) : aucune seconde
version de la forme des données, donc aucune divergence possible entre ce
qu'un plan montre chez lui et ce qu'il montre ailleurs.

Côté lecture, `apps.search.distant` sert ces instantanés sous
``/api/exploration/distant/<instance:slug>/…`` avec les chemins de l'API des
plans, et le frontend y redirige les appels de ses écrans réels.
"""

import json

from rest_framework.renderers import JSONRenderer

from apps.plans.exploration import CLE_ACCES, elaguer
from apps.plans.models_enjeux import Enjeu
from apps.plans.serializers import PlanGestionDetailSerializer
from apps.plans.serializers_operations import OperationSerializer
from apps.plans.views_enjeux import EnjeuViewSet, payload_enjeux_du_plan
from apps.plans.views_operations import (
    OperationViewSet, operations_du_plan, payload_operations_du_plan,
)

#: Version de la forme des instantanés. À incrémenter si un lecteur ancien
#: risquait de mal comprendre un instantané récent, ou l'inverse.
ECRANS_VERSION = 1


def ecrans_du_plan(plan):
    """
    Les réponses d'API des écrans réels d'un plan, élaguées (#683).

    ``plan`` : réponse de ``plans/by-slug/{slug}/`` ;
    ``enjeux`` : réponse de ``enjeux/by-plan/{id}/`` ;
    ``operations_par_type`` : réponse de ``operations/by-plan/{id}/`` ;
    ``operations`` : réponse de ``operations/{id}/`` pour chaque action,
    indexée par identifiant.

    Tout passe par :func:`elaguer` : budget, RH, financement, mesures,
    réalisations, fichiers, personnes et commentaires ne sortent pas d'ici —
    `TestEcransPubliesCloisonnement` le vérifie par fragments de nom.
    """
    enjeux = EnjeuViewSet._with_deep_prefetch(Enjeu.objects.filter(id_pg=plan))
    operations = operations_du_plan(plan, OperationViewSet.queryset)

    instantanes = {
        'version': ECRANS_VERSION,
        'plan': PlanGestionDetailSerializer(plan).data,
        'enjeux': payload_enjeux_du_plan(plan, enjeux),
        'operations_par_type': payload_operations_du_plan(plan, operations),
        'operations': {
            str(operation.pk): OperationSerializer(operation).data
            for operation in operations
        },
    }
    # Rendu JSON puis relu : les sérialiseurs laissent des `Decimal`, des dates
    # et des géométries que seul l'encodeur de DRF sait écrire — l'instantané
    # doit être du JSON pur, stockable tel quel par le hub.
    elague = elaguer(json.loads(JSONRenderer().render(instantanes)))
    # Ce que lit un plan distant est, par construction, une lecture
    # d'exploration : les écrans masquent ce que l'API n'a pas envoyé.
    for cle in ('plan', 'enjeux'):
        elague[cle][CLE_ACCES] = True
    for operation in elague['operations'].values():
        operation[CLE_ACCES] = True
    return elague
