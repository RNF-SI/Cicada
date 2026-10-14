"""
API vues pour les infos système (version, mise à jour).
Accessibles via JWT, réservées au super_admin.
"""
import json
from pathlib import Path

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status

from config.version import __version__
from rest_framework.permissions import IsAuthenticated

from apps.users.permissions import IsSuperAdmin


# Fichiers d'échange avec l'hôte (dossier /var/lib/cicada/updates du serveur,
# monté ici sous /var/lib/cicada) : écrits par cicada-heartbeat et cicada-updater,
# lus par l'application ; le déclencheur est écrit par l'application.
UPDATE_AVAILABLE_FILE = Path("/var/lib/cicada/update_available.json")
UPDATE_TRIGGER_FILE = Path("/var/lib/cicada/update_trigger.json")
UPDATE_RESULT_FILE = Path("/var/lib/cicada/update_result.json")


def _read_json(path: Path):
    """Contenu JSON du fichier, ou None s'il est absent ou illisible."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _version_key(version):
    """« 0.1.51 » → (0, 1, 51) ; None si ce n'est pas un numéro de version."""
    try:
        return tuple(int(part) for part in str(version).split('.'))
    except (TypeError, ValueError):
        return None


def get_update_info():
    """
    État de la mise à jour, vu par la page d'administration.

    La version installée est celle de l'application elle-même (``__version__``),
    pas celle notée par le dernier heartbeat : juste après une mise à jour, le
    heartbeat n'est pas encore passé et son fichier dit encore l'ancienne
    version. La mise à jour n'est « disponible » que si la version annoncée est
    plus récente que celle qui tourne.
    """
    announced = _read_json(UPDATE_AVAILABLE_FILE) or {}
    current = __version__ if __version__ != "0.0.0" else announced.get('current_version', __version__)
    latest = announced.get('latest_version')
    latest_key, current_key = _version_key(latest), _version_key(current)
    if latest_key and current_key:
        update_available = latest_key > current_key
    else:
        update_available = bool(announced.get('update_available', False))
    return {
        'current_version': current,
        'update_available': update_available,
        'latest_version': latest,
        'last_check': announced.get('last_check'),
        # Déclencheur déposé par le bouton et pas encore consommé par l'updater
        'update_pending': UPDATE_TRIGGER_FILE.exists(),
        # Dernière mise à jour faite par l'updater : success, version, timestamp, error
        'last_update': _read_json(UPDATE_RESULT_FILE),
    }


class SystemVersionView(APIView):
    """
    GET /api/system/version/
    Retourne la version actuelle et, le cas échéant, la dernière version disponible.
    Super admin uniquement.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request: Request) -> Response:
        return Response(get_update_info())


class SystemAppVersionView(APIView):
    """
    GET /api/system/app-version/
    Version de l'application, pour l'afficher dans l'administration (#646).

    Endpoint distinct de SystemVersionView : celle-ci reste réservée au super
    admin car elle porte aussi l'état de mise à jour, en pendant du bouton qui
    la déclenche. Le pied de la sidebar d'administration, lui, est vu par le
    référent et l'admin organisme — d'où une réponse limitée à la version.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response({'version': __version__})


class SystemTriggerUpdateView(APIView):
    """
    POST /api/system/trigger-update/
    Body: { "version": "0.1.13" }
    Crée le fichier trigger pour que cicada-updater effectue la mise à jour.
    Super admin uniquement.
    """
    permission_classes = [IsSuperAdmin]

    def post(self, request: Request) -> Response:
        version = request.data.get('version') if isinstance(request.data, dict) else None
        if not version:
            return Response(
                {'error': 'Version requise'},
                status=status.HTTP_400_BAD_REQUEST
            )
        trigger_file = UPDATE_TRIGGER_FILE
        try:
            trigger_file.write_text(json.dumps({
                'version': version,
                'requested_by': request.user.email,
            }))
        except OSError as e:
            return Response(
                {'error': f'Impossible d\'écrire le trigger: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response({
            'success': True,
            'message': f'Mise à jour vers {version} programmée. Elle sera effectuée dans quelques instants.',
        })
