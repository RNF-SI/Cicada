"""
Raccordement de l'instance au hub, vu par un super administrateur (#696, #698).

Cinq endpoints sous `/api/federation/raccordement/`, alimentant l'encart
« Exploration fédérée » de Administration > Paramètres :

- `GET` — l'état complet : configuration effective, adhésion, dernières
  publications et un diagnostic qui dit **en une phrase** ce qui ne va pas ;
- `POST verifier/` — interroge le hub en direct ;
- `POST adhesion/` — demande l'adhésion à l'exploration nationale ;
- `POST confirmation/` — relaie au suivi le code de confirmation que RNF a
  envoyé par e-mail ; code juste ⇒ adhésion acceptée et enrôlement sur le hub ;
- `POST contact/` — message de l'administrateur connecté à RNF.

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

from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import IsSuperAdmin

from . import raccordement

logger = logging.getLogger(__name__)


class RaccordementView(APIView):
    """`GET /api/federation/raccordement/`."""

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(raccordement.etat())


class RaccordementVerifierView(APIView):
    """`POST /api/federation/raccordement/verifier/`."""

    permission_classes = [IsSuperAdmin]

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

    def post(self, request):
        try:
            raccordement.contacter_rnf(request.user, request.data)
        except raccordement.ErreurRaccordement as erreur:
            return _erreur(erreur)
        except Exception:  # noqa: BLE001
            return _inattendue("Message à RNF")
        return Response({'statut': 'envoye'}, status=202)
