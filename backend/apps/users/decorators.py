"""
Décorateurs pour la gestion des permissions dans les vues.
"""
from functools import wraps
from django.http import JsonResponse
from rest_framework import status


def require_super_admin(view_func):
    """
    Décorateur qui requiert les permissions Super Administrateur.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user and request.user.is_authenticated):
            return JsonResponse(
                {'error': 'Authentification requise'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not request.user.is_super_admin():
            return JsonResponse(
                {'error': 'Permissions Super Administrateur requises'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        return view_func(request, *args, **kwargs)
    return wrapper


def require_admin_organisme(view_func):
    """
    Décorateur qui requiert les permissions Administrateur d'organisme ou plus.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user and request.user.is_authenticated):
            return JsonResponse(
                {'error': 'Authentification requise'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not request.user.is_admin_organisme():
            return JsonResponse(
                {'error': 'Permissions Administrateur d\'organisme requises'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        return view_func(request, *args, **kwargs)
    return wrapper


def require_referent(view_func):
    """
    Décorateur qui requiert les permissions Référent ou plus.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user and request.user.is_authenticated):
            return JsonResponse(
                {'error': 'Authentification requise'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not request.user.is_referent():
            return JsonResponse(
                {'error': 'Permissions Référent requises'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        return view_func(request, *args, **kwargs)
    return wrapper


def require_organisme_access(organisme_param='organisme_id'):
    """
    Décorateur qui vérifie l'accès à un organisme spécifique.
    
    Args:
        organisme_param: Nom du paramètre contenant l'ID de l'organisme
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not (request.user and request.user.is_authenticated):
                return JsonResponse(
                    {'error': 'Authentification requise'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Récupérer l'ID de l'organisme depuis les paramètres
            organisme_id = kwargs.get(organisme_param)
            if not organisme_id:
                return JsonResponse(
                    {'error': 'ID organisme manquant'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Importer ici pour éviter les imports circulaires
            from .models import BibOrganismes
            
            try:
                organisme = BibOrganismes.objects.get(id_organisme=organisme_id)
            except BibOrganismes.DoesNotExist:
                return JsonResponse(
                    {'error': 'Organisme non trouvé'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Vérifier les permissions
            if not request.user.can_manage_organisme(organisme):
                return JsonResponse(
                    {'error': 'Accès non autorisé à cet organisme'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_site_access(site_param='site_id'):
    """
    Décorateur qui vérifie l'accès à un site spécifique.
    
    Args:
        site_param: Nom du paramètre contenant l'ID du site
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not (request.user and request.user.is_authenticated):
                return JsonResponse(
                    {'error': 'Authentification requise'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Récupérer l'ID du site depuis les paramètres
            site_id = kwargs.get(site_param)
            if not site_id:
                return JsonResponse(
                    {'error': 'ID site manquant'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Importer ici pour éviter les imports circulaires
            from .models import Site
            
            try:
                site = Site.objects.get(id_site=site_id)
            except Site.DoesNotExist:
                return JsonResponse(
                    {'error': 'Site non trouvé'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Vérifier les permissions
            if not request.user.can_manage_site(site):
                return JsonResponse(
                    {'error': 'Accès non autorisé à ce site'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_same_organisme(view_func):
    """
    Décorateur qui vérifie que l'utilisateur appartient au même organisme
    que l'objet qu'il tente d'accéder.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user and request.user.is_authenticated):
            return JsonResponse(
                {'error': 'Authentification requise'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Super admin passe toujours
        if request.user.is_super_admin():
            return view_func(request, *args, **kwargs)
        
        # Cette vérification sera complétée selon le contexte spécifique
        # dans les vues qui utilisent ce décorateur
        return view_func(request, *args, **kwargs)
    return wrapper