"""
Connexion GeoNature / UsersHub réglée depuis Administration > Paramètres (#769).

Super admin uniquement. Le mot de passe du compte de lecture n'est jamais
renvoyé (seulement ``mot_de_passe_defini``) ni journalisé.

    GET   /api/auth/connexion-geonature/            état
    PATCH /api/auth/connexion-geonature/            saisie des réglages
    POST  /api/auth/connexion-geonature/tester/     essai, sans rien écrire
    POST  /api/auth/connexion-geonature/activer/    {confirmer} → mode GeoNature
    POST  /api/auth/connexion-geonature/desactiver/ {confirmer} → comptes CICADA
"""
import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsSuperAdmin

from . import reglages

logger = logging.getLogger(__name__)

TAG = 'Authentification'

ETAT = inline_serializer('EtatConnexionGeoNature', fields={
    'mode': serializers.ChoiceField(choices=reglages.MODES, help_text="Mode de connexion en service"),
    'configuree': serializers.BooleanField(help_text="Base UsersHub et code d'application renseignés"),
    'base_sur_ce_serveur': serializers.BooleanField(),
    'valeurs': serializers.DictField(help_text="Réglages effectifs, sans le mot de passe"),
    'mot_de_passe_defini': serializers.BooleanField(),
    'origines': serializers.DictField(help_text="Par champ : environnement (verrouillé), base ou null"),
    'modifie_le': serializers.DateTimeField(allow_null=True),
    'modifie_par': serializers.CharField(allow_null=True),
})

RESULTAT_TEST = inline_serializer('TestConnexionGeoNature', fields={
    'ok': serializers.BooleanField(),
    'erreur': serializers.CharField(allow_null=True, help_text="Code stable : mot_de_passe, pg_hba, delai…"),
    'message': serializers.CharField(),
    'chiffree': serializers.BooleanField(allow_null=True),
    'application': serializers.BooleanField(allow_null=True),
    'bilan': serializers.DictField(allow_null=True, help_text="Comptes CICADA actifs autorisés / refusés"),
    'vous': serializers.DictField(allow_null=True, help_text="Le compte qui teste pourra-t-il se connecter ?"),
})

ERREUR = inline_serializer('ErreurConnexionGeoNature', fields={
    'code': serializers.CharField(),
    'detail': serializers.CharField(),
    'test': serializers.DictField(required=False),
})

CONFIRMER = inline_serializer('ConfirmerConnexionGeoNature', fields={
    'confirmer': serializers.BooleanField(required=False, default=False),
})


def _erreur(exc):
    corps = {'code': exc.code, 'detail': exc.message}
    if exc.detail is not None:
        corps['test'] = exc.detail
    return Response(corps, status=exc.status_code)


class ConnexionGeoNatureReglagesView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(operation_id='auth_connexion_geonature_etat', tags=[TAG],
                   summary="État de la connexion GeoNature / UsersHub",
                   responses={200: ETAT})
    def get(self, request):
        return Response(reglages.etat())

    @extend_schema(
        operation_id='auth_connexion_geonature_configurer', tags=[TAG],
        summary="Saisir les réglages de la connexion GeoNature / UsersHub",
        description=(
            "Champs facultatifs : libelle, organismes_exclus, code_application, db_host, db_port, "
            "db_name, db_user, db_password (chiffré, jamais relu), effacer_mot_de_passe, db_sslmode. "
            "Une valeur fixée par le `.env` ne se modifie pas ici (409 `valeur_environnement`). "
            "Connexion GeoNature active : la nouvelle configuration est testée d'abord (400 "
            "`test_echoue`, 409 `enfermement`)."
        ),
        request=inline_serializer('ReglagesConnexionGeoNature', fields={
            champ: serializers.CharField(required=False, allow_blank=True)
            for champ in (*reglages.CHAMPS, 'db_password')
        }),
        responses={200: ETAT, 400: ERREUR, 409: ERREUR},
    )
    def patch(self, request):
        try:
            reglages.configurer(request.data, request.user)
        except reglages.ErreurReglage as exc:
            return _erreur(exc)
        return Response(reglages.etat())


class ConnexionGeoNatureTestView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(operation_id='auth_connexion_geonature_tester', tags=[TAG],
                   summary="Tester la base UsersHub (sans rien écrire)", request=None,
                   responses={200: RESULTAT_TEST})
    def post(self, request):
        return Response(reglages.tester(reglages.actuels(), request.user))


class ConnexionGeoNatureActiverView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id='auth_connexion_geonature_activer', tags=[TAG],
        summary="Activer la connexion GeoNature / UsersHub",
        description=(
            "Refusée si le test échoue (400 `test_echoue`) ou si le compte qui active ne pourrait "
            "pas se connecter (409 `enfermement`). Des comptes actifs seraient refusés : 409 "
            "`confirmation_requise` tant que `confirmer` n'est pas vrai."
        ),
        request=CONFIRMER, responses={200: RESULTAT_TEST, 400: ERREUR, 409: ERREUR},
    )
    def post(self, request):
        try:
            resultat = reglages.activer(request.user, bool(request.data.get('confirmer')))
        except reglages.ErreurReglage as exc:
            return _erreur(exc)
        return Response(resultat)


class ConnexionGeoNatureDesactiverView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id='auth_connexion_geonature_desactiver', tags=[TAG],
        summary="Revenir aux comptes CICADA (email + mot de passe)",
        description="409 `mot_de_passe_requis` si le compte n'a pas de mot de passe CICADA, "
                    "tant que `confirmer` n'est pas vrai.",
        request=CONFIRMER, responses={200: ETAT, 409: OpenApiResponse(response=ERREUR)},
    )
    def post(self, request):
        try:
            reglages.desactiver(request.user, bool(request.data.get('confirmer')))
        except reglages.ErreurReglage as exc:
            return _erreur(exc)
        return Response(reglages.etat())
