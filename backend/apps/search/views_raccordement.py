"""
Raccordement de l'instance au hub, vu par un super administrateur (#696, #698).

Trois endpoints sous `/api/federation/raccordement/`, alimentant l'encart
« Exploration fédérée » de Administration > Paramètres :

- `GET` — l'état complet : configuration effective, adhésion, dernières
  publications et un diagnostic qui dit **en une phrase** ce qui ne va pas ;
- `POST verifier/` — interroge le hub en direct ;
- `POST adhesion/` — demande l'adhésion à l'exploration nationale.

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


class RaccordementAdhesionView(APIView):
    """`POST /api/federation/raccordement/adhesion/`."""

    permission_classes = [IsSuperAdmin]

    def post(self, request):
        try:
            raccordement.demander_adhesion()
        except raccordement.ErreurRaccordement as erreur:
            return Response(
                {'erreur': erreur.cle, 'detail': erreur.message},
                status=erreur.statut_http,
            )
        except Exception:  # noqa: BLE001 — une page d'admin doit recevoir une clé
            logger.exception("Demande d'adhésion au hub : erreur inattendue.")
            return Response(
                {'erreur': 'erreur_inconnue', 'detail': "Erreur inattendue."},
                status=500,
            )
        # Pas d'actualisation : la demande vient d'être envoyée, relire le
        # suivi dans la même seconde ne ferait que doubler l'attente.
        return Response(raccordement.etat(actualiser=False))
