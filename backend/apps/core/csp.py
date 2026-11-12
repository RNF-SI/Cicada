"""Rapports de la politique de sécurité du contenu (CSP en observation).

Le navigateur envoie ici chaque écart à la politique ``Report-Only`` : ils
arrivent dans le journal ``csp`` au lieu de ne se voir que dans la console de
chaque poste. Route anonyme par nature (le navigateur n'envoie pas de jeton) :
corps borné, débit borné, rien n'est écrit en base.
"""
import json
import logging

from django.core.cache import cache
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger('csp')

TAILLE_MAX = 8 * 1024
RAPPORTS_PAR_MINUTE = 120


@csrf_exempt
@require_POST
def rapport_csp(request):
    try:
        cache.add('csp-rapports', 0, 60)
        if cache.incr('csp-rapports') > RAPPORTS_PAR_MINUTE:
            return HttpResponse(status=204)
    except Exception:
        pass
    corps = request.body[:TAILLE_MAX + 1]
    if len(corps) > TAILLE_MAX:
        return HttpResponse(status=413)
    try:
        rapport = json.loads(corps.decode('utf-8', errors='replace')).get('csp-report', {})
    except (ValueError, AttributeError):
        return HttpResponse(status=400)
    if isinstance(rapport, dict):
        logger.warning(
            'CSP: %s bloquerait %s sur %s',
            str(rapport.get('violated-directive') or rapport.get('effective-directive'))[:100],
            str(rapport.get('blocked-uri'))[:200],
            str(rapport.get('document-uri'))[:200],
        )
    return HttpResponse(status=204)
