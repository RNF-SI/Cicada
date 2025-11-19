"""
Middleware pour la gestion des permissions.
"""
import json
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework import status


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
    Middleware pour l'audit des actions utilisateur.
    """
    
    def process_request(self, request):
        """
        Log des actions importantes pour l'audit.
        """
        # Actions à auditer
        audit_paths = [
            '/api/users/',
            '/api/organismes/',
            '/api/sites/',
            '/api/plans/',
        ]
        
        # Méthodes importantes à auditer
        audit_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
        
        should_audit = (
            any(request.path.startswith(path) for path in audit_paths) and
            request.method in audit_methods
        )
        
        if should_audit and request.user and request.user.is_authenticated:
            # Stocker l'information d'audit dans la requête pour utilisation ultérieure
            request.audit_info = {
                'user_id': request.user.id_role,
                'user_email': request.user.email,
                'action': request.method,
                'path': request.path,
                'timestamp': None,  # Sera rempli dans process_response
            }
        
        return None
    
    def process_response(self, request, response):
        """
        Finalise l'audit après traitement de la requête.
        """
        if hasattr(request, 'audit_info'):
            from datetime import datetime
            request.audit_info['timestamp'] = datetime.now()
            request.audit_info['status_code'] = response.status_code
            
            # TODO: Implémenter le stockage des logs d'audit
            # logger.info("AUDIT", extra=request.audit_info)
            
        return response