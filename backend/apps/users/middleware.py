"""
Middleware pour la gestion des permissions.
"""
import json
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status


# Logger pour l'audit
audit_logger = logging.getLogger('audit')


class PermissionMiddleware(MiddlewareMixin):
    """
    Middleware pour vérifier les permissions de base et ajouter des informations
    de contexte utilisateur.
    """
    
    # URLs qui ne nécessitent pas d'authentification
    EXEMPT_URLS = [
        '/admin/',
        '/api/auth/login/',
        '/api/auth/health/',
        '/api/health/',
    ]
    
    def process_request(self, request):
        """
        Traitement de la requête entrante.
        """
        # Ignorer les URLs exemptées
        for exempt_url in self.EXEMPT_URLS:
            if request.path.startswith(exempt_url):
                return None
        
        # Ne pas traiter ici l'authentification car DRF s'en charge
        # Ce middleware se contente d'ajouter des informations dans process_response
        return None
    
    def process_response(self, request, response):
        """
        Traitement de la réponse sortante.
        Ajoute des en-têtes d'information utilisateur si authentifié.
        """
        try:
            if (hasattr(request, 'user') and 
                request.user and 
                request.user.is_authenticated and 
                hasattr(request.user, 'role_level') and
                request.path.startswith('/api/')):
                
                # Ajouter des informations sur les permissions de l'utilisateur
                response['X-User-Role'] = request.user.role_level
                response['X-User-Organisme'] = str(request.user.id_organisme.id_organisme) if request.user.id_organisme else 'None'
                response['X-User-Permissions'] = json.dumps({
                    'is_super_admin': request.user.is_super_admin(),
                    'is_admin_organisme': request.user.is_admin_organisme(),
                    'is_referent': request.user.is_referent(),
                })
        except Exception:
            # En cas d'erreur, ne pas faire planter la requête
            pass
        
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware pour ajouter des en-têtes de sécurité.
    """
    
    def process_response(self, request, response):
        """
        Ajoute des en-têtes de sécurité à toutes les réponses.
        """
        # Protection contre les attaques XSS
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Pour les APIs, ajouter les en-têtes CORS appropriés
        if request.path.startswith('/api/'):
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Accept, Content-Type, Authorization, X-Requested-With'
        
        return response


class AuditMiddleware(MiddlewareMixin):
    """
    Journal d'audit (``audit.log``) : chaque écriture de l'API, avec son auteur.

    Tout se fait **après** la vue : l'utilisateur d'une requête de l'API n'est
    connu qu'une fois DRF passé (jeton JWT) ; lu avant, il était toujours anonyme
    et aucune écriture n'était journalisée.
    """

    METHODES = ('POST', 'PUT', 'PATCH', 'DELETE')

    def process_response(self, request, response):
        if request.method not in self.METHODES or not request.path.startswith('/api/'):
            return response
        user = getattr(request, 'user', None)
        authentifie = bool(user is not None and getattr(user, 'is_authenticated', False))
        if not authentifie and response.status_code < 400:
            # Écritures anonymes réussies (inscription, demande de lien…) : les
            # connexions ont leur propre journal (apps.authentication.journal_connexion).
            return response
        from datetime import datetime
        from apps.authentication.echecs import adresse
        info = {
            'user_id': getattr(user, 'pk', None) if authentifie else None,
            'user_email': getattr(user, 'email', None) if authentifie else None,
            'action': request.method,
            'path': request.path,
            'ip': adresse(request),
            'timestamp': datetime.now().isoformat(),
            'status_code': response.status_code,
            'success': 200 <= response.status_code < 400,
        }
        jeton = getattr(request, 'auth', None)
        if jeton is not None and hasattr(jeton, 'get'):
            info['impersonator_id'] = jeton.get('impersonator_id')
        audit_logger.log(
            logging.INFO if info['success'] else logging.WARNING,
            f"AUDIT: {request.method} {request.path} {response.status_code} user={info['user_id']}",
            extra=info,
        )
        return response
