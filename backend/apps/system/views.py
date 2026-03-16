"""
Vues pour l'interface d'administration système
"""
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import json
import requests
from pathlib import Path
from config.version import __version__


def get_tracking_api_url():
    """
    Lit l'URL de l'API de suivi :
    - En dev : depuis variable d'environnement TRACKING_API_URL
    - En production (package) : depuis /etc/cicada/cicada.conf (fixée dans le package)
    """
    import os
    import configparser
    
    if os.path.exists('/etc/cicada/cicada.conf'):
        config = configparser.ConfigParser()
        config.read('/etc/cicada/cicada.conf')
        return config.get('CICADA', 'TRACKING_API_URL')
    else:
        return os.environ.get('TRACKING_API_URL', 'https://tracking.cicada.rnf.fr/api')


@staff_member_required
def system_info(request):
    """Page d'informations système"""
    update_info = get_update_info()
    rgpd_info = get_rgpd_info()

    return render(request, 'system/system_info.html', {
        'current_version': __version__,
        'update_info': update_info,
        'rgpd_info': rgpd_info,
    })


def get_update_info():
    """Récupère les infos de mise à jour"""
    update_file = Path("/var/lib/cicada/update_available.json")
    if update_file.exists():
        return json.loads(update_file.read_text())
    return {'update_available': False, 'current_version': __version__}


def get_rgpd_info():
    """Récupère les infos RGPD depuis l'API"""
    try:
        token = Path("/etc/cicada/instance_token").read_text().strip()
        tracking_url = get_tracking_api_url()
        response = requests.get(
            f"{tracking_url}/instances/me/",
            headers={'X-Instance-Token': token},
            timeout=10
        )
        if response.ok:
            data = response.json()
            return {
                'consent_given': data.get('rgpd_consent', False),
                'admin_name': data.get('admin_name'),
                'admin_email': data.get('admin_email'),
                'structure_name': data.get('structure_name'),
            }
    except Exception:
        pass
    return {'consent_given': False}


@staff_member_required
@require_http_methods(["POST"])
def trigger_update(request):
    """Crée un fichier trigger pour la mise à jour (sécurisé, pas de sudo)"""
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permissions insuffisantes'}, status=403)

    data = json.loads(request.body)
    version = data.get('version')

    if not version:
        return JsonResponse({'error': 'Version requise'}, status=400)

    # Écrire le trigger (le service root s'en occupera)
    trigger_file = Path("/var/lib/cicada/update_trigger.json")
    trigger_file.write_text(json.dumps({
        'version': version,
        'requested_at': str(request.user.email),
        'requested_by': request.user.email
    }))

    return JsonResponse({
        'success': True,
        'message': f'Mise à jour vers {version} programmée'
    })


@staff_member_required
@require_http_methods(["POST"])
def withdraw_consent(request):
    """Retire le consentement RGPD"""
    try:
        token = Path("/etc/cicada/instance_token").read_text().strip()
        tracking_url = get_tracking_api_url()
        response = requests.delete(
            f"{tracking_url}/instances/me/",
            headers={'X-Instance-Token': token},
            timeout=10
        )
        if response.ok:
            return JsonResponse({
                'success': True,
                'message': 'Consentement RGPD retiré avec succès'
            })
        else:
            return JsonResponse({'error': 'Erreur lors du retrait du consentement'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
