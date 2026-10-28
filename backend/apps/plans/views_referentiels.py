"""
Éléments à actualiser après un passage de PressRef, TaxRef ou HabRef (#779).

- `GET /api/plans/referentiels/a-actualiser/` : par référentiel puis par plan,
  les objets à choisir (ancien code conservé), actualisés, changés automatiquement ;
- `POST /api/plans/referentiels/objets/{id}/actualiser/` : pose le code choisi
  (permis hors brouillon : seul ce code change) ;
- `POST /api/plans/referentiels/accepter-propositions/` : équivalents uniques.

Les types d'action ont leurs propres routes (`views_referentiel.py`).
"""
from collections import defaultdict

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models_referentiel import PassageReferentielObjet
from .referentiels import moteur
from .referentiels.cibles import CIBLES


class OptionCodeSerializer(serializers.Serializer):
    code = serializers.CharField()
    libelle = serializers.CharField(allow_blank=True)


class ElementAActualiserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    cible = serializers.CharField()
    cible_libelle = serializers.CharField()
    contexte = serializers.CharField()
    statut = serializers.CharField()
    confiance = serializers.CharField()
    ancien_code = serializers.CharField()
    ancien_libelle = serializers.CharField(allow_blank=True)
    code_actuel = serializers.CharField(allow_blank=True)
    libelle_actuel = serializers.CharField(allow_blank=True)
    options = OptionCodeSerializer(many=True)
    note = serializers.CharField(allow_blank=True)
    actualise_par = serializers.CharField(allow_null=True)
    actualise_le = serializers.DateTimeField(allow_null=True)


class PlanElementsSerializer(serializers.Serializer):
    id_pg = serializers.IntegerField(allow_null=True)
    nom = serializers.CharField()
    slug = serializers.CharField(allow_null=True)
    statut = serializers.CharField(allow_null=True)
    a_actualiser = ElementAActualiserSerializer(many=True)
    actualisees = ElementAActualiserSerializer(many=True)
    automatiques = ElementAActualiserSerializer(many=True)


class ReferentielElementsSerializer(serializers.Serializer):
    code = serializers.CharField()
    libelle = serializers.CharField()
    passage = serializers.JSONField()
    total_a_actualiser = serializers.IntegerField()
    plans = PlanElementsSerializer(many=True)


class ReferentielsAActualiserSerializer(serializers.Serializer):
    referentiels = ReferentielElementsSerializer(many=True)


def _contexte(obj) -> str:
    """Ce que l'utilisateur reconnaît : l'enjeu, la pression, le suivi."""
    from django.apps import apps
    cible = CIBLES[obj.cible]
    try:
        if obj.cible == 'pression':
            p = apps.get_model('plans', 'Pression').objects.filter(pk=obj.objet_id).first()
            return p.libelle if p else ''
        if obj.cible == 'suivi_habitat':
            s = apps.get_model('plans', 'SuiviInventaire').objects.filter(pk=obj.objet_id).first()
            return f"Suivi « {s.intitule} »" if s else ''
        M = cible._modele()
        o = M.objects.select_related(cible.parent).filter(pk=obj.objet_id).first()
        return cible._contexte(o) if o else ''
    except Exception:  # noqa: BLE001 — un contexte manquant ne bloque pas la liste
        return ''


def _element(ref, obj) -> dict:
    return {
        'id': obj.pk, 'cible': obj.cible, 'cible_libelle': CIBLES[obj.cible].libelle,
        'contexte': _contexte(obj), 'statut': obj.statut, 'confiance': obj.confiance,
        'ancien_code': obj.ancien_code, 'ancien_libelle': obj.ancien_libelle,
        'code_actuel': moteur.code_courant(obj),
        'libelle_actuel': (obj.ancien_libelle if obj.statut == PassageReferentielObjet.STATUT_A_ACTUALISER
                           else obj.nouveau_libelle),
        'options': moteur.options_de(ref, obj), 'note': obj.note,
        'actualise_par': obj.actualise_par.get_full_name() if obj.actualise_par else None,
        'actualise_le': obj.actualise_le,
    }


def _objets_visibles(ref, user, plan_id=None):
    from .models import PlanGestion
    from .referentiel_actions import plans_q_pour

    objets = (moteur.objets_courants(ref)
              .select_related('plan', 'actualise_par', 'passage__cible', 'passage__source')
              .order_by('plan__nom', 'cible', 'pk'))
    q = plans_q_pour(user)
    if q is not None:
        objets = objets.filter(plan__in=PlanGestion.objects.filter(q))
    if plan_id:
        objets = objets.filter(plan_id=plan_id)
    return objets


class ReferentielsAActualiserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['plans'],
        summary="Éléments à actualiser après un passage de PressRef, TaxRef ou HabRef (#779)",
        parameters=[OpenApiParameter('plan', OpenApiTypes.INT, OpenApiParameter.QUERY, required=False)],
        responses={200: ReferentielsAActualiserSerializer},
    )
    def get(self, request):
        plan_id = request.query_params.get('plan')
        plan_id = int(plan_id) if plan_id and plan_id.isdigit() else None
        cle = {PassageReferentielObjet.STATUT_A_ACTUALISER: 'a_actualiser',
               PassageReferentielObjet.STATUT_ACTUALISE: 'actualisees',
               PassageReferentielObjet.STATUT_APPLIQUE: 'automatiques'}
        resultat = []
        for ref in moteur.REFERENTIELS.values():
            objets = list(_objets_visibles(ref, request.user, plan_id))
            if not objets:
                continue
            passage = objets[0].passage
            groupes = defaultdict(lambda: {'a_actualiser': [], 'actualisees': [], 'automatiques': []})
            plans = {}
            for obj in objets:
                plans[obj.plan_id] = obj.plan
                groupes[obj.plan_id][cle[obj.statut]].append(_element(ref, obj))
            liste = [{'id_pg': plans[pid].pk if plans[pid] else None,
                      'nom': plans[pid].nom if plans[pid] else "Hors plan (responsabilités de site)",
                      'slug': plans[pid].slug if plans[pid] else None,
                      'statut': plans[pid].statut if plans[pid] else None, **g}
                     for pid, g in groupes.items()]
            liste.sort(key=lambda p: (-len(p['a_actualiser']), p['nom']))
            resultat.append({
                'code': ref.code, 'libelle': ref.libelle,
                'passage': {'depuis': passage.source.libelle, 'vers': passage.cible.libelle,
                            'date': passage.date_application},
                'total_a_actualiser': sum(len(p['a_actualiser']) for p in liste),
                'plans': liste,
            })
        return Response({'referentiels': resultat})


class ActualiserElementSerializer(serializers.Serializer):
    code = serializers.CharField()
    attendu = serializers.CharField(allow_blank=True)


class ActualiserElementView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['plans'],
        summary="Choisir le nouveau code d'un élément à actualiser (#779)",
        description=("Pose le code choisi, y compris dans un plan validé ou archivé (seul ce code "
                     "change). `attendu` = le code affiché à l'ouverture ; 409 `code_deja_modifie` "
                     "s'il a changé entre-temps."),
        request=ActualiserElementSerializer,
        responses={200: ElementAActualiserSerializer, 400: OpenApiResponse(description="Code inconnu"),
                   403: OpenApiResponse(description="Hors des plans de l'utilisateur"),
                   409: OpenApiResponse(description="Code choisi entre-temps")},
    )
    def post(self, request, pk):
        obj = (PassageReferentielObjet.objects.select_related('passage__cible', 'plan')
               .filter(pk=pk).exclude(cible='').first())
        if obj is None or obj.passage.cible.courante is False:
            return Response({'detail': "Élément introuvable."}, status=status.HTTP_404_NOT_FOUND)
        if not moteur.peut_actualiser(request.user, obj):
            return Response({'detail': "Seuls les référents du plan choisissent ce code."},
                            status=status.HTTP_403_FORBIDDEN)
        data = ActualiserElementSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        ref = moteur.referentiel(obj.passage.cible.referentiel)
        try:
            obj = moteur.actualiser(ref, obj, data.validated_data['code'], request.user,
                                    attendu=data.validated_data['attendu'])
        except moteur.CodeDejaModifie as e:
            qui = e.obj.actualise_par.get_full_name() if e.obj.actualise_par else "un autre référent"
            return Response({'code': 'code_deja_modifie', 'actualise_par': qui,
                             'code_actuel': moteur.code_courant(e.obj),
                             'detail': f"Le code de cet élément vient d'être choisi par {qui}."},
                            status=status.HTTP_409_CONFLICT)
        except moteur.ReferentielErreur as e:
            return Response({'code': [str(e)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(_element(ref, obj))


class AccepterPropositionsReferentielSerializer(serializers.Serializer):
    referentiel = serializers.CharField()
    plan = serializers.IntegerField(required=False, allow_null=True)


class AccepterPropositionsReferentielView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['plans'],
        summary="Accepter toutes les propositions d'un référentiel (#779)",
        request=AccepterPropositionsReferentielSerializer,
        responses={200: OpenApiResponse(description="{acceptees, plusieurs_options, suivi_requis}")},
    )
    def post(self, request):
        data = AccepterPropositionsReferentielSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            ref = moteur.referentiel(data.validated_data['referentiel'])
        except moteur.ReferentielErreur as e:
            return Response({'referentiel': [str(e)]}, status=status.HTTP_400_BAD_REQUEST)
        return Response(moteur.accepter_propositions(ref, request.user, data.validated_data.get('plan')))


def comptes_generiques(user) -> list[dict]:
    """Pour le bandeau : par référentiel, éléments à choisir et changés automatiquement."""
    out = []
    for ref in moteur.REFERENTIELS.values():
        objets = _objets_visibles(ref, user)
        total = objets.filter(statut=PassageReferentielObjet.STATUT_A_ACTUALISER).count()
        auto = objets.filter(statut=PassageReferentielObjet.STATUT_APPLIQUE).count()
        if total or auto:
            out.append({'code': ref.code, 'libelle': ref.libelle, 'total': total, 'automatiques': auto})
    return out
