"""
Permissions personnalisées pour l'application.
"""
from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    """
    Permission pour les Super Administrateurs uniquement.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_super_admin()
        )


class IsAdminOrganisme(BasePermission):
    """
    Permission pour les Administrateurs d'organisme et plus.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_admin_organisme()
        )


class IsReferent(BasePermission):
    """
    Permission pour les Référents et plus.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_referent()
        )


class CanManageOrganisme(BasePermission):
    """
    Permission pour gérer un organisme spécifique.
    L'ID de l'organisme doit être dans les kwargs de la vue.
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Super admin peut tout gérer
        if request.user.is_super_admin():
            return True
        
        return True  # La vérification détaillée se fait dans has_object_permission
    
    def has_object_permission(self, request, view, obj):
        """
        Vérifie les permissions sur un organisme spécifique.
        """
        return request.user.can_manage_organisme(obj)


class CanManageSite(BasePermission):
    """
    Permission pour gérer un site spécifique.
    """
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        
        # Super admin peut tout gérer
        if request.user.is_super_admin():
            return True
        
        return True  # La vérification détaillée se fait dans has_object_permission
    
    def has_object_permission(self, request, view, obj):
        """
        Vérifie les permissions sur un site spécifique.
        """
        return request.user.can_manage_site(obj)


class IsOwnerOrReadOnly(BasePermission):
    """
    Permission qui permet seulement aux propriétaires d'un objet de le modifier.
    """
    
    def has_object_permission(self, request, view, obj):
        # Lecture autorisée pour tous les utilisateurs authentifiés
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return request.user and request.user.is_authenticated
        
        # Écriture seulement pour le propriétaire ou les admins
        if hasattr(obj, 'id_role'):
            return (
                obj.id_role == request.user or 
                request.user.is_admin_organisme()
            )
        
        return request.user.is_admin_organisme()


class IsOrganismeMember(BasePermission):
    """
    Permission pour les membres d'un organisme donné.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Vérifie si l'utilisateur fait partie du même organisme que l'objet.
        """
        if request.user.is_super_admin():
            return True
        
        # Vérifier selon le type d'objet
        if hasattr(obj, 'id_organisme'):
            return obj.id_organisme == request.user.id_organisme
        elif hasattr(obj, 'organisme'):
            return obj.organisme == request.user.id_organisme
        
        return False


class HasPlanGestionAccess(BasePermission):
    """
    Permission spécifique pour l'accès aux plans de gestion.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """
        Vérifie l'accès à un plan de gestion spécifique.
        """
        user = request.user
        
        # Super admin a accès à tout
        if user.is_super_admin():
            return True
        
        # Pour un plan de gestion, vérifier les sites associés
        if hasattr(obj, 'sites'):
            # Si l'utilisateur peut gérer au moins un des sites du plan
            # obj.sites.all() renvoie des CorSitePg, donc on accède à .site
            for cor_site in obj.sites.all():
                if user.can_manage_site(cor_site.site):
                    return True
        
        return False