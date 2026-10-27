"""
« Actions à actualiser » après un passage du référentiel des types d'action (#751).

- `GET /api/plans/referentiel-actions/a-actualiser/` : les actions des plans
  de l'utilisateur dont le type est à choisir, celles déjà actualisées (et par
  qui), et celles changées automatiquement sur une correspondance probable.
- `POST /api/plans/operations/{id}/actualiser-type/` : pose le type choisi
  (cf. `OperationViewSet.actualiser_type`).
"""
from collections import defaultdict

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .models_referentiel import PassageReferentielActions, PassageReferentielObjet
from . import referentiel_actions as ref


class ActionAActualiserSerializer(serializers.Serializer):
    id_operation = serializers.IntegerField()
    libelle = serializers.CharField()
    code_affichage = serializers.CharField(allow_null=True)
    enjeu_slug = serializers.CharField(allow_null=True)
    statut = serializers.CharField()
    confiance = serializers.CharField()
    ancien_code = serializers.CharField()
    ancien_libelle = serializers.CharField()
    suggestion_code = serializers.CharField()
    suggestion_libelle = serializers.CharField()
    suggestion_id = serializers.IntegerField(allow_null=True)
    note = serializers.CharField()
    type_actuel_id = serializers.IntegerField(allow_null=True)
    type_actuel_code = serializers.CharField(allow_null=True)
    type_actuel_libelle = serializers.CharField(allow_null=True)
    actualise_par = serializers.CharField(allow_null=True)
    actualise_le = serializers.DateTimeField(allow_null=True)


class PlanAActualiserSerializer(serializers.Serializer):
    id_pg = serializers.IntegerField(allow_null=True)
    nom = serializers.CharField()
    slug = serializers.CharField(allow_null=True)
    statut = serializers.CharField(allow_null=True)
    a_actualiser = ActionAActualiserSerializer(many=True)
    actualisees = ActionAActualiserSerializer(many=True)
    automatiques = ActionAActualiserSerializer(many=True)


class AActualiserReponseSerializer(serializers.Serializer):
    passage = serializers.JSONField(allow_null=True)
    total_a_actualiser = serializers.IntegerField()
    plans = PlanAActualiserSerializer(many=True)


def _item(obj, suggestions, enjeux):
    op = obj.operation
    t = op.id_type_action
    sugg = suggestions.get(obj.suggestion_code)
    from .serializers_operations import _compute_operation_code_affichage

    return {
        'id_operation': op.pk,
        'libelle': op.libelle,
        'code_affichage': _compute_operation_code_affichage(op),
        'enjeu_slug': enjeux.get(op.pk),
        'statut': obj.statut,
        'confiance': obj.confiance,
        'ancien_code': obj.ancien_code,
        'ancien_libelle': obj.ancien_libelle,
        'suggestion_code': obj.suggestion_code,
        'suggestion_libelle': sugg.label if sugg else '',
        'suggestion_id': sugg.pk if sugg else None,
        'note': obj.note,
        'type_actuel_id': t.pk if t else None,
        'type_actuel_code': t.cd_nomenclature if t else None,
        'type_actuel_libelle': t.label if t else None,
        'actualise_par': obj.actualise_par.get_full_name() if obj.actualise_par else None,
        'actualise_le': obj.actualise_le,
    }


def _enjeu_slugs(operations) -> dict:
    """Slug d'un enjeu de chaque action, pour ouvrir sa fiche."""
    from .serializers_operations import _operation_enjeu_slug

    out = {}
    for op in operations:
        try:
            out[op.pk] = _operation_enjeu_slug(op)
        except Exception:  # noqa: BLE001 — une action sans enjeu reste listée
            out[op.pk] = None
    return out


class ActionsAActualiserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['plans'],
        summary="Actions dont le type est à actualiser (#751)",
        description=(
            "Après un passage du référentiel des types d'action : par plan de l'utilisateur, "
            "les actions sans équivalent certain (type à choisir), celles déjà actualisées "
            "et celles changées automatiquement sur une correspondance probable."
        ),
        parameters=[OpenApiParameter('plan', OpenApiTypes.INT, OpenApiParameter.QUERY,
                                     required=False, description="Un seul plan")],
        responses={200: AActualiserReponseSerializer},
    )
    def get(self, request):
        from apps.core.models import Nomenclature
        from .models import PlanGestion

        passage = (PassageReferentielActions.objects
                   .filter(statut=PassageReferentielActions.STATUT_APPLIQUE,
                           cible__courante=True)
                   .select_related('source', 'cible').first())
        if passage is None:
            return Response({'passage': None, 'total_a_actualiser': 0, 'plans': []})

        objets = (passage.objets.filter(operation__isnull=False)
                  .select_related('operation__id_type_action', 'operation__id_categorie_action_reserve',
                                  'plan', 'actualise_par')
                  .order_by('plan__nom', 'operation_id'))
        q = ref.plans_q_pour(request.user)
        if q is not None:
            objets = objets.filter(plan__in=PlanGestion.objects.filter(q))
        plan_id = request.query_params.get('plan')
        if plan_id and plan_id.isdigit():
            objets = objets.filter(plan_id=int(plan_id))
        objets = [o for o in objets
                  if o.statut != PassageReferentielObjet.STATUT_APPLIQUE
                  or o.confiance == PassageReferentielObjet.CONFIANCE_PROBABLE]

        suggestions = {n.cd_nomenclature: n for n in Nomenclature.objects.filter(
            id_type__mnemonique=ref.TYPE_ACTION, actif=True,
            cd_nomenclature__in={o.suggestion_code for o in objets if o.suggestion_code})}
        enjeux = _enjeu_slugs([o.operation for o in objets])
        groupes = defaultdict(lambda: {'a_actualiser': [], 'actualisees': [], 'automatiques': []})
        plans = {}
        cle = {PassageReferentielObjet.STATUT_A_ACTUALISER: 'a_actualiser',
               PassageReferentielObjet.STATUT_ACTUALISE: 'actualisees',
               PassageReferentielObjet.STATUT_APPLIQUE: 'automatiques'}
        for o in objets:
            plans[o.plan_id] = o.plan
            groupes[o.plan_id][cle[o.statut]].append(_item(o, suggestions, enjeux))

        resultat = []
        for pid, g in groupes.items():
            plan = plans[pid]
            resultat.append({
                'id_pg': plan.pk if plan else None,
                'nom': plan.nom if plan else "Actions sans plan",
                'slug': plan.slug if plan else None,
                'statut': plan.statut if plan else None,
                **g,
            })
        resultat.sort(key=lambda p: (-len(p['a_actualiser']), p['nom']))
        return Response({
            'passage': {
                'id': passage.pk,
                'depuis': passage.source.libelle,
                'vers': passage.cible.libelle,
                'date': passage.date_application,
            },
            'total_a_actualiser': sum(len(p['a_actualiser']) for p in resultat),
            'plans': resultat,
        })


class ActualiserTypeSerializer(serializers.Serializer):
    id_type_action = serializers.IntegerField()
    type_attendu = serializers.IntegerField(required=False, allow_null=True, default=None)


ACTUALISER_TYPE_SCHEMA = extend_schema(
    tags=['plans'],
    summary="Choisir le nouveau type d'une action à actualiser (#751)",
    description=(
        "Pose le type d'action (et la catégorie qui en découle), y compris dans un plan validé : "
        "c'est la seule modification permise hors brouillon. `type_attendu` = le type affiché "
        "à l'ouverture ; s'il a changé entre-temps, réponse 409 (`type_deja_modifie`)."
    ),
    request=ActualiserTypeSerializer,
    responses={200: OpenApiResponse(description="Action mise à jour (fiche détaillée)"),
               400: OpenApiResponse(description="Type inconnu ou inactif"),
               403: OpenApiResponse(description="Hors des plans de l'utilisateur"),
               409: OpenApiResponse(description="Type choisi entre-temps par un autre référent")},
)


class CompteAActualiserSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    vers = serializers.CharField(allow_null=True)


class CompteAActualiserView(APIView):
    """Nombre d'actions des plans de l'utilisateur dont le type est à choisir :
    alimente le bandeau affiché sur toutes les pages (#751)."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['plans'],
        summary="Nombre d'actions dont le type est à actualiser (#751)",
        responses={200: CompteAActualiserSerializer},
    )
    def get(self, request):
        from .models import PlanGestion

        passage = (PassageReferentielActions.objects
                   .filter(statut=PassageReferentielActions.STATUT_APPLIQUE,
                           cible__courante=True)
                   .select_related('cible').first())
        if passage is None:
            return Response({'total': 0, 'vers': None})
        objets = passage.objets.filter(operation__isnull=False,
                                       statut=PassageReferentielObjet.STATUT_A_ACTUALISER)
        q = ref.plans_q_pour(request.user)
        if q is not None:
            objets = objets.filter(plan__in=PlanGestion.objects.filter(q))
        return Response({'total': objets.values('operation').distinct().count(),
                         'vers': passage.cible.libelle})
