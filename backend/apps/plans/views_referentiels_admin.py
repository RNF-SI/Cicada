"""
Page super-admin « Référentiels » (#777) : l'état et les passages de version de
chaque référentiel — types d'action (Gestref), PressRef, TaxRef, HabRef —,
distincts de la mise à jour de l'application.

- `GET  /api/plans/referentiels/admin/` : versions en service, versions
  disponibles (dossiers livrés), passage en cours et sa progression ;
- `POST /api/plans/referentiels/admin/<ref>/simuler|appliquer|annuler/` :
  `{version, sans_email?}`. Rien ne se fait au démarrage : seul ce geste (ou la
  commande `passage_referentiel`) change les données d'une instance.
"""
import json

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsSuperAdmin

from . import referentiel_actions as ra
from .models_referentiel import (
    REFERENTIEL_TYPES_ACTION, PassageReferentielActions, PassageReferentielObjet,
)
from .referentiels import moteur

TYPES_ACTION = 'TYPE_ACTION'


def _versions_types_action() -> list[dict]:
    out = []
    dossier = ra.DOSSIER_REFERENTIELS
    for p in sorted(dossier.iterdir()) if dossier.is_dir() else []:
        f = p / 'version.json'
        if f.exists():
            meta = json.loads(f.read_text(encoding='utf-8'))
            out.append({'nom': p.name, **{k: meta.get(k) for k in ('code', 'libelle', 'depuis')}})
    return out


def _versions_generiques(ref) -> list[dict]:
    out = []
    for nom in moteur.versions_disponibles(ref):
        meta = json.loads((moteur.DOSSIER_VERSIONS / ref.dossier / nom / 'version.json')
                          .read_text(encoding='utf-8'))
        out.append({'nom': nom, **{k: meta.get(k) for k in ('code', 'libelle', 'depuis')}})
    return out


def _progression(passage) -> dict | None:
    if passage is None:
        return None
    objets = passage.objets.all()
    if passage.cible.referentiel == REFERENTIEL_TYPES_ACTION:
        objets = objets.filter(operation__isnull=False)
    S = PassageReferentielObjet
    return {
        'id': passage.pk, 'depuis': passage.source.libelle, 'vers': passage.cible.libelle,
        'vers_code': passage.cible.code, 'date': passage.date_application,
        'a_actualiser': objets.filter(statut=S.STATUT_A_ACTUALISER).count(),
        'automatiques': objets.filter(statut=S.STATUT_APPLIQUE).count(),
        'actualises': objets.filter(statut=S.STATUT_ACTUALISE).count(),
    }


def _passage_courant(code):
    return (PassageReferentielActions.objects
            .filter(statut=PassageReferentielActions.STATUT_APPLIQUE, cible__courante=True,
                    cible__referentiel=code)
            .select_related('source', 'cible').first())


def etat() -> list[dict]:
    lignes = []
    courante = ra.version_courante()
    code_ta = courante.code if courante else ra.VERSION_INITIALE
    libelle_ta = courante.libelle if courante else ra.LIBELLE_INITIAL
    lignes.append({
        'code': TYPES_ACTION, 'libelle': "Types d'action (Gestref)",
        'en_service': {'code': code_ta, 'libelle': libelle_ta},
        'versions': [{**v, 'applicable': v['depuis'] == code_ta, 'en_service': v['code'] == code_ta}
                     for v in _versions_types_action()],
        'passage': _progression(_passage_courant(TYPES_ACTION)),
    })
    for ref in moteur.REFERENTIELS.values():
        code, libelle = moteur.version_en_service(ref)
        lignes.append({
            'code': ref.code, 'libelle': ref.libelle,
            'en_service': {'code': code, 'libelle': libelle},
            'versions': [{**v, 'applicable': v['depuis'] == code, 'en_service': v['code'] == code}
                         for v in _versions_generiques(ref)],
            'passage': _progression(_passage_courant(ref.code)),
        })
    return lignes


class EtatReferentielsView(APIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    @extend_schema(tags=['administration'], summary="Référentiels : versions et passages (#777)",
                   responses={200: OpenApiResponse(description="Liste des référentiels")})
    def get(self, request):
        return Response({'referentiels': etat()})


class PassageDemandeSerializer(serializers.Serializer):
    version = serializers.CharField()
    sans_email = serializers.BooleanField(required=False, default=False)


def _simuler(code, nom):
    if code == TYPES_ACTION:
        return ra.simuler(ra.charger_version(nom))
    ref = moteur.referentiel(code)
    return moteur.simuler(ref, moteur.charger(ref, nom))


def _appliquer(code, nom, sans_email):
    if code == TYPES_ACTION:
        return ra.appliquer(ra.charger_version(nom), envoyer_email=not sans_email)
    ref = moteur.referentiel(code)
    return moteur.appliquer(ref, moteur.charger(ref, nom), envoyer_email=not sans_email)


def _annuler(code, nom):
    if code == TYPES_ACTION:
        return ra.annuler(ra.charger_version(nom))
    ref = moteur.referentiel(code)
    return moteur.annuler(ref, moteur.charger(ref, nom))


ERREURS = (ra.ReferentielErreur, moteur.ReferentielErreur)


class PassageReferentielView(APIView):
    """`action` : simuler | appliquer | annuler."""

    permission_classes = [IsAuthenticated, IsSuperAdmin]

    @extend_schema(tags=['administration'], summary="Simuler, appliquer ou annuler un passage (#777)",
                   request=PassageDemandeSerializer,
                   responses={200: OpenApiResponse(description="Rapport de simulation ou passage"),
                              400: OpenApiResponse(description="Version inutilisable ou incohérente")})
    def post(self, request, code, action):
        data = PassageDemandeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        nom, code = data.validated_data['version'], code.upper()
        try:
            if action == 'simuler':
                return Response({'rapport': _simuler(code, nom)})
            if action == 'appliquer':
                passage = _appliquer(code, nom, data.validated_data['sans_email'])
            elif action == 'annuler':
                passage = _annuler(code, nom)
            else:
                return Response({'detail': "Action inconnue."}, status=status.HTTP_404_NOT_FOUND)
        except ERREURS as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'passage': {'id': passage.pk, 'resume': passage.resume,
                                     'statut': passage.statut},
                         'referentiels': etat()})
