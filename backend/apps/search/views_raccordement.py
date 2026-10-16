"""
Raccordement de l'instance au hub, vu par un super administrateur (#696, #698).

Six endpoints sous `/api/federation/raccordement/`, alimentant l'encart
« Exploration fédérée » de Administration > Paramètres :

- `GET` — l'état complet : configuration effective, adhésion, dernières
  publications et un diagnostic qui dit **en une phrase** ce qui ne va pas ;
- `POST verifier/` — interroge le hub en direct ;
- `POST adhesion/` — demande l'adhésion à l'exploration nationale ;
- `POST confirmation/` — relaie au suivi le code de confirmation que RNF a
  envoyé par e-mail ; code juste ⇒ adhésion acceptée et enrôlement sur le hub ;
- `POST contact/` — message de l'administrateur connecté à RNF ;
- `PATCH configuration/` — URL du hub, jetons et relais saisis à la main (#695).

Le code de confirmation ne transite que dans la requête `confirmation/` : il
n'est ni stocké, ni journalisé, ni renvoyé.

Réservé au super administrateur : demander l'adhésion engage la structure, et
l'état décrit la configuration du serveur. Aucune réponse ne contient de jeton
ni d'empreinte — les formes sont construites champ par champ dans
`apps.search.raccordement`, jamais à partir d'un modèle sérialisé en bloc.

Les erreurs portent une clé stable (`erreur`) que l'interface traduit, et un
`detail` lisible pour qui appelle l'API à la main.
"""

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsSuperAdmin

from . import raccordement, schema

logger = logging.getLogger(__name__)


class RaccordementView(APIView):
    """`GET /api/federation/raccordement/`."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id='federation_raccordement_retrieve',
        summary="État du raccordement au hub",
        description=(
            "Configuration effective, adhésion, dernières publications et un "
            "`diagnostic` qui dit en une clé ce qui bloque. Une adhésion en attente "
            "est d'abord actualisée auprès du suivi RNF. Aucun jeton ni empreinte "
            "n'est jamais renvoyé."
        ),
        responses={200: schema.ETAT_RACCORDEMENT, 401: schema.REPONSE_401,
                   403: schema.REPONSES_RACCORDEMENT_ERREURS[403]},
        tags=[schema.TAG_FEDERATION],
    )
    def get(self, request):
        return Response(raccordement.etat())


class RaccordementVerifierView(APIView):
    """`POST /api/federation/raccordement/verifier/`."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id='federation_raccordement_verifier',
        summary="Interroger le hub en direct",
        description=(
            "Le hub est-il joignable, cette instance y est-elle reconnue et active, "
            "quand a-t-elle publié pour la dernière fois ? Rien n'est écrit. "
            "`instance_reconnue` reste nul si l'instance n'a aucun jeton à présenter."
        ),
        request=None,
        responses={200: schema.VERIFICATION_HUB, 401: schema.REPONSE_401,
                   403: schema.REPONSES_RACCORDEMENT_ERREURS[403]},
        tags=[schema.TAG_FEDERATION],
    )
    def post(self, request):
        return Response(raccordement.verifier_hub())


def _erreur(erreur):
    return Response(erreur.corps(), status=erreur.statut_http)


def _inattendue(contexte):
    logger.exception("%s : erreur inattendue.", contexte)
    return Response({'erreur': 'erreur_inconnue', 'detail': "Erreur inattendue."}, status=500)


class RaccordementAdhesionView(APIView):
    """`POST /api/federation/raccordement/adhesion/` — corps : contact de l'administrateur."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id='federation_raccordement_adhesion',
        summary="Demander l'adhésion à l'exploration nationale",
        description=(
            "Engage la structure : coche le consentement au partage, tire les jetons "
            "et transmet leurs empreintes au suivi RNF avec le contact de "
            "l'administrateur. Refusé (409) si des jetons viennent déjà de "
            "l'environnement ou si l'adhésion est acceptée ; 400 si l'identité de "
            "l'instance (`CICADA_INSTANCE_ID`/`LABEL`) manque. Renvoie l'état complet."
        ),
        request=schema.REQUETE_ADHESION,
        responses={200: schema.ETAT_RACCORDEMENT, **schema.REPONSES_RACCORDEMENT_ERREURS},
        tags=[schema.TAG_FEDERATION],
    )
    def post(self, request):
        try:
            raccordement.demander_adhesion(request.data)
        except raccordement.ErreurRaccordement as erreur:
            return _erreur(erreur)
        except Exception:  # noqa: BLE001 — une page d'admin doit recevoir une clé
            return _inattendue("Demande d'adhésion au hub")
        # Pas d'actualisation : la demande vient d'être envoyée, relire le
        # suivi dans la même seconde ne ferait que doubler l'attente.
        return Response(raccordement.etat(actualiser=False))


class RaccordementConfirmationView(APIView):
    """`POST /api/federation/raccordement/confirmation/` — corps : `{code}`."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id='federation_raccordement_confirmation',
        summary="Confirmer l'adhésion avec le code reçu par e-mail",
        description=(
            "Relaie le code au suivi RNF ; code juste ⇒ adhésion acceptée et instance "
            "enrôlée sur le hub. Le code ne transite que dans cette requête : ni "
            "stocké, ni journalisé, ni renvoyé. Renvoie l'état complet."
        ),
        request=schema.REQUETE_CONFIRMATION,
        responses={200: schema.ETAT_RACCORDEMENT, **schema.REPONSES_RACCORDEMENT_ERREURS},
        tags=[schema.TAG_FEDERATION],
    )
    def post(self, request):
        try:
            donnees = request.data if isinstance(request.data, dict) else {}
            raccordement.confirmer_adhesion(donnees.get('code'))
        except raccordement.ErreurRaccordement as erreur:
            return _erreur(erreur)
        except Exception:  # noqa: BLE001
            # `logger.exception` ne journalise que la pile : jamais le corps
            # de la requête, donc jamais le code.
            return _inattendue("Confirmation d'adhésion au hub")
        return Response(raccordement.etat(actualiser=False))


class RaccordementContactView(APIView):
    """`POST /api/federation/raccordement/contact/` — corps : `{sujet, message}`."""

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id='federation_raccordement_contact',
        summary="Écrire à RNF",
        description=(
            "Message de l'administrateur connecté, transmis par le suivi RNF. "
            "L'expéditeur (nom, adresse) est celui du compte connecté, jamais du corps."
        ),
        request=schema.REQUETE_CONTACT,
        responses={202: schema.REPONSE_CONTACT, **schema.REPONSES_RACCORDEMENT_ERREURS},
        tags=[schema.TAG_FEDERATION],
    )
    def post(self, request):
        try:
            raccordement.contacter_rnf(request.user, request.data)
        except raccordement.ErreurRaccordement as erreur:
            return _erreur(erreur)
        except Exception:  # noqa: BLE001
            return _inattendue("Message à RNF")
        return Response({'statut': 'envoye'}, status=202)


class RaccordementConfigurationView(APIView):
    """
    `PATCH /api/federation/raccordement/configuration/` (#695).

    Corps : `hub_url`, `jeton_depot`, `jeton_lecture`, `effacer_jetons`,
    `exploration_source` — tous facultatifs. Rend l'état complet, qui ne
    contient jamais les jetons : seulement `jeton_*_defini` et leur origine.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id='federation_raccordement_configuration',
        summary="Saisir le raccordement au hub",
        description=(
            "URL du hub, jetons délivrés par `enroler_instance` (chiffrés en base, "
            "jamais relus) et source de l'exploration. Une valeur fixée par le "
            "`.env` ne se modifie pas ici (409 `valeur_environnement`). Rend l'état "
            "complet, sans jeton."
        ),
        request=schema.REQUETE_CONFIGURATION,
        responses={200: schema.ETAT_RACCORDEMENT, **schema.REPONSES_RACCORDEMENT_ERREURS},
        tags=[schema.TAG_FEDERATION],
    )
    def patch(self, request):
        try:
            raccordement.configurer(request.data)
        except raccordement.ErreurRaccordement as erreur:
            return _erreur(erreur)
        except Exception:  # noqa: BLE001
            # Pile seule, jamais le corps : il porte les jetons.
            return _inattendue("Saisie du raccordement au hub")
        return Response(raccordement.etat(actualiser=False))
