"""
Vues d'exemple pour démontrer le système de permissions.
"""
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .permissions import (
    IsSuperAdmin, IsAdminOrganisme, IsReferent, 
    CanManageOrganisme, CanManageSite
)
from .decorators import (
    require_super_admin, require_admin_organisme, 
    require_referent, require_organisme_access, require_site_access
)
from .models import Role, BibOrganismes, Site


# Vue de démonstration des permissions (non utilisée par le frontend) : hors schéma OpenAPI.
@extend_schema(exclude=True)
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def super_admin_only_view(request):
    """
    Vue accessible uniquement aux Super Administrateurs.
    Exemple d'utilisation des permissions DRF.
    """
    users_count = Role.objects.count()
    return Response({
        'message': 'Accès Super Admin OK',
        'user': request.user.email,
        'role_level': request.user.role_level,
        'total_users': users_count
    })


# Vue de démonstration des permissions (non utilisée par le frontend) : hors schéma OpenAPI.
@extend_schema(exclude=True)
@api_view(['GET'])
@permission_classes([IsAdminOrganisme])
def admin_organisme_view(request):
    """
    Vue accessible aux Administrateurs d'organisme et plus.
    """
    organisme = request.user.id_organisme
    organisme_name = organisme.nom_organisme if organisme else "Aucun"
    
    return Response({
        'message': 'Accès Admin Organisme OK',
        'user': request.user.email,
        'organisme': organisme_name,
        'permissions': {
            'is_super_admin': request.user.is_super_admin(),
            'is_admin_organisme': request.user.is_admin_organisme(),
            'is_referent': request.user.is_referent(),
        }
    })


# Vue de démonstration des permissions (non utilisée par le frontend) : hors schéma OpenAPI.
@extend_schema(exclude=True)
@api_view(['GET'])
@permission_classes([IsReferent])
def referent_view(request):
    """
    Vue accessible aux Référents et plus.
    """
    return Response({
        'message': 'Accès Référent OK',
        'user': request.user.email,
        'role_level': request.user.role_level
    })


# Vue de démonstration des permissions (non utilisée par le frontend) : hors schéma OpenAPI.
@extend_schema(exclude=True)
@api_view(['GET'])
@require_super_admin
def decorator_super_admin_view(request):
    """
    Vue utilisant le décorateur pour Super Admin.
    Exemple d'utilisation des décorateurs personnalisés.
    """
    return Response({
        'message': 'Accès via décorateur Super Admin OK',
        'user': request.user.email
    })


# Vue de démonstration des permissions (non utilisée par le frontend) : hors schéma OpenAPI.
@extend_schema(exclude=True)
@api_view(['GET'])
@require_admin_organisme
def decorator_admin_organisme_view(request):
    """
    Vue utilisant le décorateur pour Admin Organisme.
    """
    return Response({
        'message': 'Accès via décorateur Admin Organisme OK',
        'user': request.user.email
    })


# Vue de démonstration des permissions (non utilisée par le frontend) : hors schéma OpenAPI.
@extend_schema(exclude=True)
@api_view(['GET'])
@require_referent
def decorator_referent_view(request):
    """
    Vue utilisant le décorateur pour Référent.
    """
    return Response({
        'message': 'Accès via décorateur Référent OK',
        'user': request.user.email
    })


# Vue de démonstration des permissions d'objet (non utilisée par le frontend) : hors schéma OpenAPI.
@extend_schema(exclude=True)
@api_view(['GET'])
@require_organisme_access('organisme_id')
def organisme_detail_view(request, organisme_id):
    """
    Vue pour gérer un organisme spécifique.
    Vérifie que l'utilisateur peut gérer cet organisme.
    """
    try:
        organisme = BibOrganismes.objects.get(id_organisme=organisme_id)
        return Response({
            'message': f'Accès autorisé à l\'organisme {organisme.nom_organisme}',
            'organisme': {
                'id': organisme.id_organisme,
                'nom': organisme.nom_organisme,
                'ville': organisme.ville_organisme
            },
            'user': request.user.email,
            'can_manage': request.user.can_manage_organisme(organisme)
        })
    except BibOrganismes.DoesNotExist:
        return Response(
            {'error': 'Organisme non trouvé'}, 
            status=status.HTTP_404_NOT_FOUND
        )


# Vue de démonstration des permissions d'objet (non utilisée par le frontend) : hors schéma OpenAPI.
@extend_schema(exclude=True)
@api_view(['GET'])
@require_site_access('site_id')
def site_detail_view(request, site_id):
    """
    Vue pour gérer un site spécifique.
    Vérifie que l'utilisateur peut gérer ce site.
    """
    try:
        site = Site.objects.get(id_site=site_id)
        return Response({
            'message': f'Accès autorisé au site {site.nom_site}',
            'site': {
                'id': site.id_site,
                'nom': site.nom_site,
                'surface': site.surf_off
            },
            'user': request.user.email,
            'can_manage': request.user.can_manage_site(site)
        })
    except Site.DoesNotExist:
        return Response(
            {'error': 'Site non trouvé'}, 
            status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    tags=['users'],
    summary="Permissions de l'utilisateur connecté",
    description=(
        "Vue de diagnostic : rôle, drapeaux de permission, groupes Django et sites "
        "dont l'utilisateur est référent validé. Utile pour comprendre ce qu'un compte "
        "peut faire sans parcourir les autres endpoints."
    ),
    responses={
        200: inline_serializer(
            name='PermissionsUtilisateur',
            fields={
                'user': inline_serializer(
                    name='PermissionsUtilisateurProfil',
                    fields={
                        'id': serializers.IntegerField(),
                        'email': serializers.EmailField(),
                        'nom_complet': serializers.CharField(),
                        'role_level': serializers.CharField(),
                        'organisme': serializers.CharField(allow_null=True, help_text="Nom de l'organisme de rattachement"),
                    },
                ),
                'permissions': inline_serializer(
                    name='PermissionsUtilisateurDrapeaux',
                    fields={
                        'is_super_admin': serializers.BooleanField(),
                        'is_admin_organisme': serializers.BooleanField(),
                        'is_referent': serializers.BooleanField(),
                        'is_staff': serializers.BooleanField(),
                        'is_superuser': serializers.BooleanField(),
                        'is_active': serializers.BooleanField(),
                    },
                ),
                'groups': serializers.ListField(child=serializers.CharField(), help_text="Noms des groupes Django"),
                'managed_sites': serializers.ListField(child=inline_serializer(
                    name='SiteGere',
                    fields={'id': serializers.IntegerField(), 'nom': serializers.CharField()},
                ), help_text="Sites dont l'utilisateur est référent validé"),
            },
        ),
        401: OpenApiResponse(description="Utilisateur non authentifié."),
    },
)
@api_view(['GET'])
def permissions_info_view(request):
    """
    Vue pour obtenir des informations sur les permissions de l'utilisateur.
    """
    user = request.user
    
    if not user.is_authenticated:
        return Response(
            {'error': 'Utilisateur non authentifié'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    # Informations sur l'utilisateur
    user_info = {
        'id': user.id_role,
        'email': user.email,
        'nom_complet': user.get_full_name(),
        'role_level': user.role_level,
        'organisme': user.id_organisme.nom_organisme if user.id_organisme else None
    }
    
    # Permissions de l'utilisateur
    permissions = {
        'is_super_admin': user.is_super_admin(),
        'is_admin_organisme': user.is_admin_organisme(),
        'is_referent': user.is_referent(),
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'is_active': user.active
    }
    
    # Groupes de l'utilisateur
    groups = [group.name for group in user.groups.all()]
    
    # Sites gérés (si référent)
    managed_sites = []
    if user.is_referent():
        from .models import CorRoleSite
        cor_sites = CorRoleSite.objects.filter(
            id_role=user, 
            referent=True, 
            referent_valid=True
        ).select_related('id_site')
        managed_sites = [
            {
                'id': cor.id_site.id_site,
                'nom': cor.id_site.nom_site
            }
            for cor in cor_sites
        ]
    
    return Response({
        'user': user_info,
        'permissions': permissions,
        'groups': groups,
        'managed_sites': managed_sites
    })