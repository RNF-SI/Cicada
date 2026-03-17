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
from apps.users.permissions import IsSuperAdmin


def get_update_info():
    """Récupère les infos de mise à jour depuis le fichier écrit par le heartbeat."""
    update_file = Path("/var/lib/cicada/update_available.json")
    if update_file.exists():
        try:
            return json.loads(update_file.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {
        'update_available': False,
        'current_version': __version__,
        'latest_version': None,
        'last_check': None,
    }


class SystemVersionView(APIView):
    """
    GET /api/system/version/
    Retourne la version actuelle et, le cas échéant, la dernière version disponible.
    Super admin uniquement.
    """
    permission_classes = [IsSuperAdmin]

    def get(self, request: Request) -> Response:
        info = get_update_info()
        return Response({
            'current_version': info.get('current_version', __version__),
            'update_available': info.get('update_available', False),
            'latest_version': info.get('latest_version'),
            'last_check': info.get('last_check'),
        })


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
        trigger_file = Path("/var/lib/cicada/update_trigger.json")
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
