"""
ViewSets pour les API Organismes et Sites avec permissions et filtrage.
"""
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import BibOrganismes, Site, CorRoleSite, CorOgSite, Role
from .serializers_org_sites import (
    OrganismeListSerializer, OrganismeDetailSerializer, OrganismeCreateUpdateSerializer,
    SiteListSerializer, SiteGeoJSONSerializer, SiteDetailSerializer, SiteCreateUpdateSerializer,
    OrganismeSiteAssignmentSerializer, BulkSiteAssignmentSerializer
)
from .permissions import IsSuperAdmin, IsAdminOrganisme, IsReferent
from .pagination import StandardPagination
from .filters_org_sites import OrganismeFilter, SiteFilter


class OrganismeViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des organismes.
    
    Permissions:
    - Liste/Détail: Authentifié (filtrage selon rôle)
    - Création: Admin Organisme+
    - Modification: Admin de l'organisme OU Super Admin
    - Suppression: Super Admin seulement
    """
    
    pagination_class = StandardPagination
    filterset_class = OrganismeFilter
    search_fields = ['nom_organisme', 'ville_organisme', 'email_organisme']
    ordering_fields = ['nom_organisme', 'ville_organisme']
    ordering = ['nom_organisme']
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action."""
        if self.action == 'list':
            return OrganismeListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return OrganismeCreateUpdateSerializer
        else:
            return OrganismeDetailSerializer
    
    def get_permissions(self):
        """Permissions selon l'action."""
        if self.action in ['public']:
            # L'endpoint public est accessible sans authentification
            permission_classes = [permissions.AllowAny]
        elif self.action in ['create']:
            permission_classes = [IsAdminOrganisme]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsAdminOrganisme]  # Vérifié dans get_object
        elif self.action in ['destroy']:
            permission_classes = [IsSuperAdmin]
        else:
            permission_classes = [permissions.IsAuthenticated]

        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filtrage selon le rôle de l'utilisateur.

        Paramètres GET:
        - for_invite: Si 'true', permet aux référents de voir tous les organismes
                      pour la fonctionnalité d'invitation d'organisme à un site.
        """
        user = self.request.user
        for_invite = self.request.query_params.get('for_invite', '').lower() == 'true'

        if user.is_super_admin() or user.is_redacteur_principal():
            # Super admin et rédacteur principal voient tous les organismes
            return BibOrganismes.objects.all().select_related('id_parent')

        elif user.is_admin_organisme() and user.id_organisme:
            # Admin organisme voit tous les organismes pour invitation,
            # sinon son organisme et ses enfants
            if for_invite:
                return BibOrganismes.objects.all().select_related('id_parent')

            org_ids = [user.id_organisme.id_organisme]

            # Ajouter les organismes enfants
            children = BibOrganismes.objects.filter(id_parent=user.id_organisme)
            org_ids.extend(children.values_list('id_organisme', flat=True))

            return BibOrganismes.objects.filter(
                id_organisme__in=org_ids
            ).select_related('id_parent')

        elif user.is_referent() and user.id_organisme:
            # Référent voit tous les organismes pour invitation,
            # sinon seulement son organisme
            if for_invite:
                return BibOrganismes.objects.all().select_related('id_parent')

            return BibOrganismes.objects.filter(
                id_organisme=user.id_organisme.id_organisme
            ).select_related('id_parent')

        else:
            # Utilisateur normal voit seulement son organisme
            if user.id_organisme:
                return BibOrganismes.objects.filter(
                    id_organisme=user.id_organisme.id_organisme
                ).select_related('id_parent')

        return BibOrganismes.objects.none()
    
    def get_object(self):
        """Vérification des permissions d'objet."""
        obj = super().get_object()
        user = self.request.user
        
        # Super admin peut tout faire
        if user.is_super_admin():
            return obj
        
        # Admin organisme peut modifier son organisme et ses enfants
        if user.is_admin_organisme() and user.id_organisme:
            if (obj.id_organisme == user.id_organisme.id_organisme or 
                obj.id_parent == user.id_organisme):
                return obj
        
        # Pour les autres actions (lecture), utiliser get_queryset
        if self.action in ['retrieve']:
            return obj
        
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied("Vous n'avez pas la permission de modifier cet organisme.")
    
    def perform_create(self, serializer):
        """Logique de création d'organisme."""
        user = self.request.user
        
        # Admin organisme ne peut créer que des enfants de son organisme
        if user.is_admin_organisme() and not user.is_super_admin():
            # Forcer l'organisme parent
            serializer.save(id_parent=user.id_organisme)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrganisme])
    def assign_site(self, request, pk=None):
        """
        Assigne un site à un organisme ou met à jour le statut principal.
        POST /api/users/organismes/{id}/assign_site/
        Body: { "site_id": 123, "principal": true/false }
        """
        organisme = self.get_object()
        serializer = OrganismeSiteAssignmentSerializer(data=request.data)

        if serializer.is_valid():
            site_id = serializer.validated_data['site_id']
            principal = serializer.validated_data.get('principal', False)
            site = get_object_or_404(Site, id_site=site_id)

            # Vérifier les permissions
            if not request.user.is_super_admin():
                # Admin_og peut assigner un site à son propre organisme
                if request.user.is_admin_organisme() and request.user.id_organisme:
                    # Vérifier que c'est bien son organisme
                    if organisme.id_organisme != request.user.id_organisme.id_organisme:
                        return Response(
                            {'error': 'Vous ne pouvez assigner des sites qu\'à votre propre organisme.'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    # Seul super_admin peut modifier le statut principal
                    if principal:
                        return Response(
                            {'error': 'Seul un super administrateur peut définir un organisme comme gestionnaire principal.'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                else:
                    # Pour les autres rôles, vérifier can_manage_site
                    if not request.user.can_manage_site(site):
                        return Response(
                            {'error': 'Vous ne pouvez pas gérer ce site.'},
                            status=status.HTTP_403_FORBIDDEN
                        )

            # Créer ou mettre à jour la relation (principal est géré par le save() du modèle)
            cor_og_site, created = CorOgSite.objects.update_or_create(
                uuid_og=organisme,
                id_site=site,
                defaults={'principal': principal}
            )

            if created:
                message = f'Site {site.nom_site} assigné à {organisme.nom_organisme}'
                if principal:
                    message += ' comme gestionnaire principal'
                return Response(
                    {'message': message, 'principal': principal},
                    status=status.HTTP_201_CREATED
                )
            else:
                message = f'Relation mise à jour pour {site.nom_site}'
                if principal:
                    message = f'{organisme.nom_organisme} est maintenant le gestionnaire principal de {site.nom_site}'
                return Response(
                    {'message': message, 'principal': cor_og_site.principal},
                    status=status.HTTP_200_OK
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrganisme])
    def bulk_assign_sites(self, request, pk=None):
        """Assignation en masse de sites à un organisme."""
        organisme = self.get_object()
        serializer = BulkSiteAssignmentSerializer(data=request.data)

        if serializer.is_valid():
            # Vérifier que l'admin_og assigne à son propre organisme
            if not request.user.is_super_admin():
                if request.user.is_admin_organisme() and request.user.id_organisme:
                    if organisme.id_organisme != request.user.id_organisme.id_organisme:
                        return Response(
                            {'error': 'Vous ne pouvez assigner des sites qu\'à votre propre organisme.'},
                            status=status.HTTP_403_FORBIDDEN
                        )

            site_ids = serializer.validated_data['site_ids']
            sites = Site.objects.filter(id_site__in=site_ids)

            results = {'assigned': [], 'already_assigned': [], 'forbidden': []}

            with transaction.atomic():
                for site in sites:
                    # Créer la relation
                    cor_og_site, created = CorOgSite.objects.get_or_create(
                        uuid_og=organisme,
                        id_site=site
                    )
                    
                    if created:
                        results['assigned'].append({
                            'id_site': site.id_site,
                            'nom_site': site.nom_site
                        })
                    else:
                        results['already_assigned'].append({
                            'id_site': site.id_site,
                            'nom_site': site.nom_site
                        })
            
            return Response(results, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete', 'post'])
    def unassign_site(self, request, pk=None, organisme_pk=None, site_pk=None):
        """
        Désassigne un site d'un organisme.

        Crée une demande de validation envoyée à l'admin_og de l'organisme à retirer.
        La suppression effective n'a lieu qu'après validation.

        Body (optionnel): { "justification": "Motif de la demande" }
        """
        from apps.notifications.models import ValidationRequest
        from apps.notifications.services import NotificationService

        # Support both pk (from router) and organisme_pk (from manual URL)
        organisme_id = pk or organisme_pk
        organisme = get_object_or_404(BibOrganismes, id_organisme=organisme_id)
        site = get_object_or_404(Site, id_site=site_pk)

        # Vérifier permissions : il faut pouvoir gérer le site
        if not request.user.is_super_admin():
            if not request.user.can_manage_site(site):
                return Response(
                    {'error': 'Vous ne pouvez pas gérer ce site.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Vérifier que le lien existe
        try:
            CorOgSite.objects.get(uuid_og=organisme, id_site=site)
        except CorOgSite.DoesNotExist:
            return Response(
                {'error': 'Ce site n\'est pas assigné à cet organisme.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Vérifier si une demande similaire est déjà en cours
        existing_request = ValidationRequest.objects.filter(
            request_type='site_org_unlink',
            target_site=site,
            requested_organisme=organisme,
            status='pending'
        ).first()

        if existing_request:
            return Response(
                {'error': 'Une demande de retrait est déjà en cours pour ce site et cet organisme.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer la justification du body si présente
        justification = request.data.get('justification', '')

        # Créer la demande de validation
        validation_request = ValidationRequest.objects.create(
            request_type='site_org_unlink',
            requester=request.user,
            target_site=site,
            requested_organisme=organisme,
            justification=justification,
            status='pending'
        )

        # Notifier les validateurs (admin_og de l'organisme à retirer)
        NotificationService.notify_validators(validation_request)

        return Response(
            {
                'message': f'Demande de retrait de {organisme.nom_organisme} du site {site.nom_site} créée.',
                'validation_request_id': validation_request.id,
                'status': 'pending'
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def sites(self, request, pk=None):
        """Liste des sites gérés par un organisme."""
        organisme = self.get_object()
        cor_sites = CorOgSite.objects.filter(uuid_og=organisme).select_related('id_site')

        sites_data = []
        for cor in cor_sites:
            site = cor.id_site
            sites_data.append({
                'id_site': site.id_site,
                'nom_site': site.nom_site,
                'surf_off': site.surf_off,
                'type_site': site.id_type_site.label if site.id_type_site else None,
                'active': site.active,
                'principal': cor.principal
            })

        return Response(sites_data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def public(self, request):
        """
        Liste publique des organismes pour l'inscription.
        GET /api/users/organismes/public/

        Retourne uniquement id et nom, sans authentification requise.
        """
        organismes = BibOrganismes.objects.all().order_by('nom_organisme')

        data = [
            {'id': org.id_organisme, 'nom_organisme': org.nom_organisme}
            for org in organismes
        ]

        return Response(data)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrganisme])
    def stats(self, request):
        """Statistiques des organismes."""
        queryset = self.get_queryset()

        total_organismes = queryset.count()

        # Statistiques par type (parent/enfant)
        organismes_parents = queryset.filter(id_parent__isnull=True).count()
        organismes_enfants = queryset.filter(id_parent__isnull=False).count()

        # BibOrganismes doesn't have 'active' field - count with sites instead
        organismes_with_sites = queryset.filter(corogsite__isnull=False).distinct().count()

        return Response({
            'total_organismes': total_organismes,
            'organismes_parents': organismes_parents,
            'organismes_enfants': organismes_enfants,
            'organismes_with_sites': organismes_with_sites
        })


class SiteViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la gestion des sites.

    Permissions:
    - Liste/Détail: Authentifié (filtrage selon rôle)
    - Création: Authentifié (le site doit être validé par admin_og/super_admin)
    - Modification: Référent du site OU Admin de l'organisme gestionnaire OU Super Admin
    - Suppression: Admin Organisme+ (dans son scope)

    Note: La création de site déclenche un workflow de validation.
    Le créateur devient automatiquement référent une fois le site validé.

    URLs: Les sites sont accessibles via leur slug (ex: /api/users/sites/reserve-naturelle-camargue/).
    """

    pagination_class = StandardPagination
    filterset_class = SiteFilter
    search_fields = ['nom_site', 'id_local', 'id_inpn', 'slug']
    ordering_fields = ['nom_site', 'surf_off', 'date_crea']
    ordering = ['nom_site']
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'
    
    def get_serializer_class(self):
        """Retourne le serializer approprié selon l'action."""
        if self.action == 'list':
            return SiteListSerializer
        elif self.action == 'geojson':
            return SiteGeoJSONSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return SiteCreateUpdateSerializer
        else:
            return SiteDetailSerializer
    
    def get_permissions(self):
        """Permissions selon l'action."""
        if self.action in ['create']:
            # Tout utilisateur authentifié peut créer un site (soumis à validation)
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsReferent]  # Vérifié dans get_object
        elif self.action in ['destroy']:
            permission_classes = [IsReferent]  # Vérifié dans get_object (super_admin, admin_og, référent du site)
        elif self.action in ['bulk_import_validate', 'bulk_import_execute', 'bulk_import_status']:
            permission_classes = [IsAdminOrganisme]
        else:
            permission_classes = [permissions.IsAuthenticated]

        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filtrage selon le rôle de l'utilisateur."""
        user = self.request.user
        
        if user.is_super_admin() or user.is_redacteur_principal():
            # Super admin et rédacteur principal voient tous les sites
            return Site.objects.all().select_related('id_type_site')

        elif user.is_admin_organisme() and user.id_organisme:
            # Admin organisme voit les sites de son organisme + ses sites personnellement assignés
            org_sites = CorOgSite.objects.filter(
                uuid_og=user.id_organisme
            ).values_list('id_site', flat=True)

            # Ajouter les sites personnellement assignés (ex: référent d'un site d'un autre organisme)
            assigned_sites = CorRoleSite.objects.filter(id_role=user).values_list('id_site', flat=True)

            return Site.objects.filter(
                Q(id_site__in=org_sites) | Q(id_site__in=assigned_sites)
            ).distinct().select_related('id_type_site')
        
        elif user.is_referent():
            # Référent voit les sites qui lui sont assignés + sites de son organisme
            assigned_sites = CorRoleSite.objects.filter(id_role=user).values_list('id_site', flat=True)
            
            queryset = Site.objects.filter(id_site__in=assigned_sites)
            
            # Ajouter les sites de son organisme si il en a un
            if user.id_organisme:
                org_sites = CorOgSite.objects.filter(
                    uuid_og=user.id_organisme
                ).values_list('id_site', flat=True)
                
                queryset = Site.objects.filter(
                    Q(id_site__in=assigned_sites) | Q(id_site__in=org_sites)
                ).distinct()
            
            return queryset.select_related('id_type_site')
        
        else:
            # Utilisateur normal voit les sites assignés + sites de son organisme
            assigned_sites = CorRoleSite.objects.filter(id_role=user).values_list('id_site', flat=True)

            if user.id_organisme:
                org_sites = CorOgSite.objects.filter(
                    uuid_og=user.id_organisme
                ).values_list('id_site', flat=True)

                return Site.objects.filter(
                    Q(id_site__in=assigned_sites) | Q(id_site__in=org_sites)
                ).distinct().select_related('id_type_site')

            # Utilisateur sans organisme voit uniquement ses sites assignés
            return Site.objects.filter(id_site__in=assigned_sites).select_related('id_type_site')
    
    def get_object(self):
        """Vérification des permissions d'objet."""
        obj = super().get_object()
        user = self.request.user

        # Super admin peut tout faire
        if user.is_super_admin():
            return obj

        # Pour modification/suppression, vérifier permissions spécifiques
        if self.action in ['update', 'partial_update', 'destroy']:
            if user.can_manage_site(obj):
                return obj

            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous n'avez pas la permission de modifier ce site.")

        # Pour lecture, utiliser get_queryset
        return obj

    def create(self, request, *args, **kwargs):
        """
        Création de site avec workflow de validation.
        - Super admin: site créé actif immédiatement, créateur devient référent
        - Autres: site créé inactif, demande de validation créée
        """
        from apps.notifications.models import ValidationRequest
        from apps.notifications.services import NotificationService

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        if user.is_super_admin():
            # Super admin: création directe sans validation
            site = serializer.save(active=True)

            # Le super admin devient référent du site
            CorRoleSite.objects.create(
                id_site=site,
                id_role=user,
                referent=True,
                referent_valid=True,
                conservateur=False,
            )

            # Lier l'organisme du créateur si existe
            if user.id_organisme:
                CorOgSite.objects.get_or_create(
                    id_site=site,
                    uuid_og=user.id_organisme,
                    defaults={'principal': True}
                )

            # Réponse standard pour super admin
            response_serializer = SiteDetailSerializer(site, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        else:
            # Autres utilisateurs: site inactif + demande de validation
            site = serializer.save(active=False)

            # Récupérer request_as_referent (défaut: True pour compatibilité ascendante)
            request_as_referent = request.data.get('request_as_referent', True)

            # Créer la demande de validation
            validation_request = ValidationRequest.objects.create(
                request_type='site_creation',
                status='pending',
                requester=user,
                target_site=site,
                justification=f"Création du site {site.nom_site}",
                request_as_referent=request_as_referent,
            )

            # Notifier les validateurs (admin_og de l'organisme du créateur + super_admin)
            NotificationService.notify_validators(validation_request)

            # Réponse avec indication de validation en attente
            response_serializer = SiteDetailSerializer(site, context={'request': request})
            response_data = response_serializer.data
            response_data['validation_pending'] = True
            response_data['validation_request_id'] = validation_request.id
            if request_as_referent:
                response_data['message'] = (
                    f"Le site \"{site.nom_site}\" a été créé et est en attente de validation. "
                    "Vous deviendrez automatiquement référent du site une fois celui-ci validé."
                )
            else:
                response_data['message'] = (
                    f"Le site \"{site.nom_site}\" a été créé et est en attente de validation. "
                    "Vous obtiendrez un accès utilisateur au site une fois celui-ci validé."
                )

            return Response(response_data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        """
        Suppression d'un site avec notifications.
        - Accessible au super_admin, admin_og et référent du site (via can_manage_site)
        - Envoie une notification aux référents et admin_og des organismes liés
        - Les plans liés (CorSitePg CASCADE) perdent leur association mais ne sont pas supprimés
        - La détection des plans orphelins est faite par la tâche hebdomadaire check_orphaned_plans
        """
        from apps.notifications.services import NotificationService

        site = self.get_object()
        site_name = site.nom_site
        site_id = site.id_site
        deleted_by = request.user

        # Capturer les référents et les organismes avant suppression (CASCADE va tout effacer)
        referent_ids = list(
            CorRoleSite.objects.filter(id_site=site, referent=True)
            .values_list('id_role', flat=True)
        )
        org_ids = list(
            CorOgSite.objects.filter(id_site=site)
            .values_list('uuid_og', flat=True)
        )

        # Suppression effective (CASCADE sur CorRoleSite, CorOgSite, CorSitePg)
        site.delete()

        # Notification post-suppression
        NotificationService.notify_site_deleted(
            site_name=site_name,
            site_id=site_id,
            deleted_by=deleted_by,
            referent_ids=referent_ids,
            org_ids=org_ids,
        )

        return Response(status=204)

    @action(detail=True, methods=['get'])
    def geojson(self, request, slug=None):
        """Retourne le site au format GeoJSON complet."""
        site = self.get_object()
        serializer = SiteGeoJSONSerializer(site)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def geojson_list(self, request):
        """Retourne tous les sites visibles au format GeoJSON."""
        queryset = self.filter_queryset(self.get_queryset())

        # Sérialiser chaque site individuellement pour obtenir une vraie liste
        # GeoFeatureModelSerializer avec many=True retourne un OrderedDict
        features = []
        for site in queryset:
            serializer = SiteGeoJSONSerializer(site)
            features.append(serializer.data)

        # Encapsuler dans une FeatureCollection GeoJSON
        geojson_data = {
            'type': 'FeatureCollection',
            'features': features,
            'properties': {
                'count': len(features)
            }
        }

        return Response(geojson_data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminOrganisme])
    def assign_user(self, request, slug=None):
        """Assigne un utilisateur au site."""
        site = self.get_object()
        
        # Vérifier que l'utilisateur peut gérer ce site
        if not request.user.can_manage_site(site):
            return Response(
                {'error': 'Vous ne pouvez pas gérer ce site.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user_id = request.data.get('user_id')
        referent = request.data.get('referent', False)
        # Si referent=True et referent_valid n'est pas explicitement passé,
        # on considère que l'assignation directe par un admin valide automatiquement le statut
        referent_valid = request.data.get('referent_valid', referent)
        conservateur = request.data.get('conservateur', False)
        
        if not user_id:
            return Response(
                {'error': 'user_id requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = Role.objects.get(id_role=user_id)
        except Role.DoesNotExist:
            return Response(
                {'error': 'Utilisateur introuvable.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Créer ou mettre à jour la relation
        cor_role_site, created = CorRoleSite.objects.update_or_create(
            id_site=site,
            id_role=user,
            defaults={
                'referent': referent,
                'referent_valid': referent_valid,
                'conservateur': conservateur
            }
        )
        
        action_word = "assigné" if created else "mis à jour"
        return Response(
            {'message': f'Utilisateur {user.email} {action_word} au site {site.nom_site}'},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['delete'])
    def unassign_user(self, request, slug=None, user_pk=None):
        """Désassigne un utilisateur du site."""
        site = self.get_object()
        
        # Vérifier permissions
        if not request.user.can_manage_site(site):
            return Response(
                {'error': 'Vous ne pouvez pas gérer ce site.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        user = get_object_or_404(Role, id_role=user_pk)
        
        try:
            cor_role_site = CorRoleSite.objects.get(id_site=site, id_role=user)
            cor_role_site.delete()
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CorRoleSite.DoesNotExist:
            return Response(
                {'error': 'Cet utilisateur n\'est pas assigné à ce site.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def users(self, request, slug=None):
        """Liste des utilisateurs assignés au site."""
        site = self.get_object()
        cor_users = CorRoleSite.objects.filter(id_site=site).select_related('id_role')
        
        users_data = []
        for cor in cor_users:
            user = cor.id_role
            users_data.append({
                'id_role': user.id_role,
                'nom_complet': f"{user.prenom_role} {user.nom_role}".strip(),
                'email': user.email,
                'role_level': user.role_level,
                'referent': cor.referent,
                'referent_valid': cor.referent_valid,
                'conservateur': cor.conservateur
            })
        
        return Response(users_data)
    
    @action(detail=True, methods=['get'])
    def organismes(self, request, slug=None):
        """Liste des organismes gestionnaires du site."""
        site = self.get_object()
        cor_orgs = CorOgSite.objects.filter(id_site=site).select_related('uuid_og')

        orgs_data = []
        for cor in cor_orgs:
            org = cor.uuid_og
            orgs_data.append({
                'id_organisme': org.id_organisme,
                'nom_organisme': org.nom_organisme,
                'ville_organisme': org.ville_organisme,
                'email_organisme': org.email_organisme,
                'principal': cor.principal
            })

        return Response(orgs_data)

    @action(detail=True, methods=['post'], permission_classes=[IsSuperAdmin])
    def set_principal_organisme(self, request, slug=None):
        """
        Définit l'organisme gestionnaire principal du site.
        POST /api/users/sites/{slug}/set_principal_organisme/
        Body: { "organisme_id": 123 }

        Seul un super admin peut modifier l'organisme principal.
        Un seul organisme peut être principal par site.
        """
        site = self.get_object()
        organisme_id = request.data.get('organisme_id')

        if not organisme_id:
            return Response(
                {'error': 'organisme_id est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            organisme = BibOrganismes.objects.get(id_organisme=organisme_id)
        except BibOrganismes.DoesNotExist:
            return Response(
                {'error': 'Organisme non trouvé.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Vérifier que l'organisme est bien lié au site
        try:
            cor_og_site = CorOgSite.objects.get(id_site=site, uuid_og=organisme)
        except CorOgSite.DoesNotExist:
            return Response(
                {'error': 'Cet organisme n\'est pas lié à ce site. Assignez-le d\'abord.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Définir comme principal (le save() retire le statut des autres)
        if cor_og_site.principal:
            return Response(
                {'message': f'{organisme.nom_organisme} est déjà le gestionnaire principal de {site.nom_site}.'},
                status=status.HTTP_200_OK
            )

        cor_og_site.principal = True
        cor_og_site.save()

        return Response({
            'message': f'{organisme.nom_organisme} est maintenant le gestionnaire principal de {site.nom_site}.',
            'site': {
                'id_site': site.id_site,
                'nom_site': site.nom_site
            },
            'organisme_principal': {
                'id_organisme': organisme.id_organisme,
                'nom_organisme': organisme.nom_organisme
            }
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def principal_organisme(self, request, slug=None):
        """
        Retourne l'organisme gestionnaire principal du site.
        GET /api/users/sites/{slug}/principal_organisme/
        """
        site = self.get_object()
        principal = CorOgSite.get_principal(site)

        if principal:
            return Response({
                'id_organisme': principal.id_organisme,
                'nom_organisme': principal.nom_organisme,
                'ville_organisme': principal.ville_organisme,
                'email_organisme': principal.email_organisme
            })
        else:
            return Response(
                {'message': 'Aucun organisme principal défini pour ce site.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], permission_classes=[IsReferent])
    def stats(self, request):
        """Statistiques des sites."""
        queryset = self.get_queryset()

        total_sites = queryset.count()
        active_sites = queryset.filter(active=True).count()
        sites_marins = queryset.filter(marin=True).count()
        sites_outre_mer = queryset.filter(outre_mer=True).count()

        # Surface totale
        from django.db.models import Sum
        surface_totale = queryset.aggregate(Sum('surf_off'))['surf_off__sum'] or 0

        return Response({
            'total_sites': total_sites,
            'active_sites': active_sites,
            'sites_marins': sites_marins,
            'sites_outre_mer': sites_outre_mer,
            'surface_totale_ha': round(surface_totale, 2)
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def check_duplicates(self, request):
        """
        Vérifie les doublons potentiels pour un site.
        GET /api/users/sites/check_duplicates/?nom_site=...&id_inpn=...

        Query params:
        - nom_site: nom du site à vérifier (recherche des noms similaires)
        - id_inpn: code INPN à vérifier (recherche exacte)
        - exclude_id: ID du site à exclure (pour édition)

        Retourne:
        - exact_inpn_match: Site avec code INPN identique (bloquant)
        - similar_names: Liste des sites avec noms similaires (avertissement)
        """
        nom_site = request.query_params.get('nom_site', '').strip()
        id_inpn = request.query_params.get('id_inpn', '').strip()
        exclude_id = request.query_params.get('exclude_id', None)

        user = request.user
        user_org = user.id_organisme

        # Initialiser la réponse
        result = {
            'exact_inpn_match': None,
            'similar_names': []
        }

        # Exclure le site courant si en mode édition
        base_queryset = Site.objects.filter(active=True).select_related('id_type_site')
        if exclude_id:
            try:
                base_queryset = base_queryset.exclude(id_site=int(exclude_id))
            except (ValueError, TypeError):
                pass

        # 1. Recherche exacte par code INPN
        if id_inpn:
            inpn_match = base_queryset.filter(id_inpn=id_inpn).first()
            if inpn_match:
                result['exact_inpn_match'] = self._build_duplicate_site_data(inpn_match, user, user_org)

        # 2. Recherche par nom similaire (si nom_site >= 3 caractères)
        if nom_site and len(nom_site) >= 3:
            # Recherche insensible à la casse
            similar_sites = base_queryset.filter(
                nom_site__icontains=nom_site
            ).exclude(
                id_site=result['exact_inpn_match']['id_site'] if result['exact_inpn_match'] else -1
            )[:10]

            for site in similar_sites:
                result['similar_names'].append(self._build_duplicate_site_data(site, user, user_org))

        return Response(result)

    def _build_duplicate_site_data(self, site, user, user_org):
        """Construit les données d'un site pour la réponse de vérification de doublons."""
        # Récupérer les organismes liés
        organismes = []
        is_user_org = False
        for cor in CorOgSite.objects.filter(id_site=site).select_related('uuid_og'):
            org = cor.uuid_og
            organismes.append({
                'id_organisme': org.id_organisme,
                'nom_organisme': org.nom_organisme,
                'principal': cor.principal
            })
            if user_org and org.id_organisme == user_org.id_organisme:
                is_user_org = True

        # Vérifier si l'utilisateur a déjà accès au site
        has_access = CorRoleSite.objects.filter(id_role=user, id_site=site).exists()

        return {
            'id_site': site.id_site,
            'slug': site.slug,
            'nom_site': site.nom_site,
            'id_inpn': site.id_inpn,
            'id_local': site.id_local,
            'type_site_label': site.id_type_site.label if site.id_type_site else None,
            'surf_off': site.surf_off,
            'organismes': organismes,
            'is_user_org': is_user_org,
            'has_access': has_access
        }

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def search_all(self, request):
        """
        Recherche dans tous les sites actifs.
        Permet aux utilisateurs de trouver des sites d'autres organismes
        pour demander un lien site-organisme.
        GET /api/users/sites/search_all/

        Query params:
        - search: terme de recherche (min 2 caractères)
        - page_size: nombre de résultats (défaut: 100, max: 500)
        """
        search = request.query_params.get('search', '').strip()

        # Retourner tous les sites actifs
        sites = Site.objects.filter(active=True).select_related('id_type_site').order_by('nom_site')

        # Filtrage par recherche si fourni
        if search and len(search) >= 2:
            sites = sites.filter(
                Q(nom_site__icontains=search) |
                Q(id_local__icontains=search) |
                Q(id_inpn__icontains=search)
            )

        # Pagination
        page_size = min(int(request.query_params.get('page_size', 100)), 500)
        sites = sites[:page_size]

        # Construire la réponse avec les organismes liés
        sites_data = []
        for site in sites:
            # Récupérer les organismes liés à ce site
            organismes = []
            for cor in CorOgSite.objects.filter(id_site=site).select_related('uuid_og'):
                organismes.append({
                    'id_organisme': cor.uuid_og.id_organisme,
                    'nom_organisme': cor.uuid_og.nom_organisme
                })

            # Récupérer les utilisateurs liés (pour vérifier l'accès côté frontend)
            users = []
            for cor in CorRoleSite.objects.filter(id_site=site).select_related('id_role'):
                users.append({
                    'id_role': cor.id_role.id_role,
                    'referent': cor.referent
                })

            sites_data.append({
                'id_site': site.id_site,
                'slug': site.slug,
                'nom_site': site.nom_site,
                'id_local': site.id_local,
                'type_site_label': site.id_type_site.label if site.id_type_site else None,
                'surf_off': site.surf_off,
                'active': site.active,
                'organismes': organismes,
                'users': users
            })

        return Response({
            'count': len(sites_data),
            'results': sites_data
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrganisme])
    def available_for_assignment(self, request):
        """
        Liste tous les sites actifs disponibles pour assignation à un organisme.
        Cet endpoint ne filtre pas par organisme, permettant aux admins d'organisme
        de voir tous les sites qu'ils peuvent potentiellement ajouter.
        GET /api/users/sites/available_for_assignment/
        """
        # Retourner tous les sites actifs sans filtrage par organisme
        sites = Site.objects.filter(active=True).select_related('id_type_site').order_by('nom_site')

        # Filtrage optionnel par recherche
        search = request.query_params.get('search', '')
        if search:
            sites = sites.filter(
                Q(nom_site__icontains=search) |
                Q(id_local__icontains=search) |
                Q(id_inpn__icontains=search)
            )

        # Pagination simple
        page_size = int(request.query_params.get('page_size', 100))
        sites = sites[:page_size]

        sites_data = []
        for site in sites:
            sites_data.append({
                'id_site': site.id_site,
                'nom_site': site.nom_site,
                'id_local': site.id_local,
                'type_site_label': site.id_type_site.label if site.id_type_site else None,
                'surf_off': site.surf_off,
                'active': site.active
            })

        return Response({
            'count': len(sites_data),
            'results': sites_data
        })

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def request_access(self, request, slug=None):
        """
        Demande l'acces a un site.
        POST /api/users/sites/{slug}/request_access/
        Body: {
            "justification": "...",  (optionnel)
            "request_as_referent": true/false  (optionnel, defaut: false)
        }
        """
        from apps.notifications.models import ValidationRequest
        from apps.notifications.services import NotificationService

        site = get_object_or_404(Site, slug=slug)

        # Verifier qu'une demande n'existe pas deja pour ce site
        existing = ValidationRequest.objects.filter(
            requester=request.user,
            request_type='site_access',
            target_site=site,
            status='pending'
        ).exists()

        if existing:
            return Response(
                {'error': 'Une demande pour ce site est deja en attente.'},
                status=status.HTTP_409_CONFLICT
            )

        # Verifier que l'utilisateur n'a pas deja acces
        already_linked = CorRoleSite.objects.filter(
            id_role=request.user,
            id_site=site
        ).exists()

        if already_linked:
            return Response(
                {'error': 'Vous avez deja acces a ce site.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Recuperer les parametres
        justification = request.data.get('justification', '')
        request_as_referent = request.data.get('request_as_referent', False)

        # Creer la demande de validation
        validation_request = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=request.user,
            target_site=site,
            justification=justification,
            request_as_referent=request_as_referent,
        )

        # Notifier les valideurs (referents du site ou admins de l'organisme)
        NotificationService.notify_validators(validation_request)

        return Response({
            'id': validation_request.id,
            'message': f'Votre demande d\'acces au site "{site.nom_site}" a ete soumise.',
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def request_referent(self, request, slug=None):
        """
        Demande a devenir referent d'un site auquel l'utilisateur a deja acces.
        POST /api/users/sites/{slug}/request_referent/
        Body: {
            "justification": "..."  (optionnel)
        }
        """
        from apps.notifications.models import ValidationRequest
        from apps.notifications.services import NotificationService

        site = get_object_or_404(Site, slug=slug)

        # Verifier que l'utilisateur est lie au site
        try:
            cor_role_site = CorRoleSite.objects.get(id_role=request.user, id_site=site)
        except CorRoleSite.DoesNotExist:
            return Response(
                {'error': 'Vous devez d\'abord avoir acces au site pour demander a devenir referent.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier que l'utilisateur n'est pas deja referent valide
        if cor_role_site.referent and cor_role_site.referent_valid:
            return Response(
                {'error': 'Vous etes deja referent de ce site.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier qu'une demande n'existe pas deja
        existing = ValidationRequest.objects.filter(
            requester=request.user,
            request_type='referent_validation',
            target_site=site,
            status='pending'
        ).exists()

        if existing:
            return Response(
                {'error': 'Une demande pour devenir referent est deja en attente.'},
                status=status.HTTP_409_CONFLICT
            )

        # Recuperer la justification
        justification = request.data.get('justification', '')

        # Creer la demande de validation
        validation_request = ValidationRequest.objects.create(
            request_type='referent_validation',
            status='pending',
            requester=request.user,
            target_site=site,
            justification=justification,
        )

        # Notifier les valideurs (referents du site, admin de l'organisme, super admin)
        NotificationService.notify_validators(validation_request)

        return Response({
            'id': validation_request.id,
            'message': f'Votre demande pour devenir referent du site "{site.nom_site}" a ete soumise.',
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def request_org_link(self, request, slug=None):
        """
        Demande de lier un site d'un autre organisme a son propre organisme.
        POST /api/users/sites/{slug}/request_org_link/
        Body: {
            "justification": "..."  (optionnel)
        }
        """
        from apps.notifications.models import ValidationRequest
        from apps.notifications.services import NotificationService

        site = get_object_or_404(Site, slug=slug)

        # Verifier que l'utilisateur a un organisme
        user_organisme = request.user.id_organisme
        if not user_organisme:
            return Response(
                {'error': 'Vous devez etre rattache a un organisme.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier que le site n'est pas deja lie a l'organisme de l'utilisateur
        already_linked = CorOgSite.objects.filter(
            id_site=site,
            uuid_og=user_organisme
        ).exists()

        if already_linked:
            return Response(
                {'error': 'Ce site est deja lie a votre organisme.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier qu'une demande n'existe pas deja
        existing = ValidationRequest.objects.filter(
            requester=request.user,
            request_type='site_org_link',
            target_site=site,
            requested_organisme=user_organisme,
            status='pending'
        ).exists()

        if existing:
            return Response(
                {'error': 'Une demande de lien pour ce site est deja en attente.'},
                status=status.HTTP_409_CONFLICT
            )

        # Recuperer la justification
        justification = request.data.get('justification', '')

        # Creer la demande de validation
        validation_request = ValidationRequest.objects.create(
            request_type='site_org_link',
            status='pending',
            requester=request.user,
            target_site=site,
            requested_organisme=user_organisme,
            justification=justification,
        )

        # Notifier les valideurs (admin de l'organisme du demandeur)
        NotificationService.notify_validators(validation_request)

        return Response({
            'id': validation_request.id,
            'message': f'Votre demande de lien avec le site "{site.nom_site}" a ete soumise.',
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def invite_organisme(self, request, slug=None):
        """
        Invite un organisme a rejoindre le site (referent uniquement).
        Le lien est cree directement sans demande de validation.
        POST /api/users/sites/{slug}/invite_organisme/
        Body: {
            "organisme_id": 123,
            "justification": "..."  (optionnel)
        }
        """
        from apps.notifications.services import NotificationService
        from apps.core.services import ActivityService

        site = get_object_or_404(Site, slug=slug)

        # Verifier que l'utilisateur est referent du site ou super_admin
        is_super_admin = request.user.is_super_admin()
        is_referent = CorRoleSite.objects.filter(
            id_site=site,
            id_role=request.user,
            referent=True,
            referent_valid=True
        ).exists()

        if not is_super_admin and not is_referent:
            return Response(
                {'error': 'Seuls les referents du site peuvent inviter des organismes.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Recuperer l'organisme a inviter
        organisme_id = request.data.get('organisme_id')
        if not organisme_id:
            return Response(
                {'error': 'L\'ID de l\'organisme est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            organisme = BibOrganismes.objects.get(id_organisme=organisme_id)
        except BibOrganismes.DoesNotExist:
            return Response(
                {'error': 'Organisme non trouve.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verifier que l'organisme n'est pas deja lie au site
        already_linked = CorOgSite.objects.filter(
            id_site=site,
            uuid_og=organisme
        ).exists()

        if already_linked:
            return Response(
                {'error': 'Cet organisme est deja lie a ce site.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Creer directement le lien organisme-site
        CorOgSite.objects.create(
            id_site=site,
            uuid_og=organisme,
            principal=False,
        )

        # Logger l'activite
        inviter_name = request.user.get_full_name() or request.user.email
        justification = request.data.get('justification', '')
        metadata = {}
        if justification:
            metadata['justification'] = justification

        ActivityService.log_site_activity(
            site=site,
            action='add_member',
            actor=request.user,
            description=f"{inviter_name} a ajoute l'organisme {organisme.nom_organisme} au site {site.nom_site}.",
            metadata=metadata,
        )

        # Notifier les parties prenantes
        NotificationService.notify_site_invitation_done(
            site=site,
            inviter=request.user,
            invited_organisme=organisme,
        )

        return Response({
            'message': f'L\'organisme "{organisme.nom_organisme}" a ete ajoute au site "{site.nom_site}".',
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def invite_user(self, request, slug=None):
        """
        Invite un utilisateur d'un organisme lie a rejoindre le site (referent uniquement).
        Le lien est cree directement sans demande de validation.
        POST /api/users/sites/{slug}/invite_user/
        Body: {
            "user_id": 123,
            "justification": "..."  (optionnel)
        }
        """
        from apps.notifications.services import NotificationService
        from apps.core.services import ActivityService

        site = get_object_or_404(Site, slug=slug)

        # Verifier que l'utilisateur est referent du site ou super_admin
        is_super_admin = request.user.is_super_admin()
        is_referent = CorRoleSite.objects.filter(
            id_site=site,
            id_role=request.user,
            referent=True,
            referent_valid=True
        ).exists()

        if not is_super_admin and not is_referent:
            return Response(
                {'error': 'Seuls les referents du site peuvent inviter des utilisateurs.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Recuperer l'utilisateur a inviter
        user_id = request.data.get('user_id')
        if not user_id:
            return Response(
                {'error': 'L\'ID de l\'utilisateur est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            target_user = Role.objects.get(id_role=user_id)
        except Role.DoesNotExist:
            return Response(
                {'error': 'Utilisateur non trouve.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verifier que l'utilisateur a un organisme
        if not target_user.id_organisme:
            return Response(
                {'error': 'L\'utilisateur doit appartenir a un organisme.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier que l'organisme de l'utilisateur est lie au site
        org_linked = CorOgSite.objects.filter(
            id_site=site,
            uuid_og=target_user.id_organisme
        ).exists()

        if not org_linked:
            return Response(
                {'error': 'L\'organisme de l\'utilisateur doit d\'abord etre lie au site.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verifier que l'utilisateur n'est pas deja lie au site
        already_linked = CorRoleSite.objects.filter(
            id_site=site,
            id_role=target_user
        ).exists()

        if already_linked:
            return Response(
                {'error': 'Cet utilisateur est deja lie a ce site.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Creer directement le lien utilisateur-site
        CorRoleSite.objects.create(
            id_site=site,
            id_role=target_user,
            referent=False,
            referent_valid=False,
            conservateur=False,
        )

        # Logger l'activite
        inviter_name = request.user.get_full_name() or request.user.email
        target_user_name = target_user.get_full_name() or target_user.email
        justification = request.data.get('justification', '')
        metadata = {}
        if justification:
            metadata['justification'] = justification

        ActivityService.log_member_change(
            site=site,
            user=target_user,
            action='add_member',
            actor=request.user,
            metadata=metadata,
        )

        # Notifier les parties prenantes
        NotificationService.notify_site_invitation_done(
            site=site,
            inviter=request.user,
            invited_user=target_user,
        )

        return Response({
            'message': f'L\'utilisateur "{target_user}" a ete ajoute au site "{site.nom_site}".',
        }, status=status.HTTP_201_CREATED)

    # ==================== IMPORT EN MASSE ====================

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrganisme],
            url_path='bulk_import_validate')
    def bulk_import_validate(self, request):
        """
        Valide un fichier d'import en masse de sites.
        POST multipart: file (.geojson, .json, .csv) + field_mapping optionnel (JSON string).

        Retourne les propriétés détectées, le mapping suggéré et la validation ligne par ligne.
        """
        from .services_bulk_import import BulkSiteImportService

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response(
                {'error': 'Aucun fichier fourni.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check file size (10 MB max)
        if uploaded_file.size > 10 * 1024 * 1024:
            return Response(
                {'error': 'Le fichier dépasse la taille maximale de 10 Mo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Determine format
        filename = uploaded_file.name.lower()
        if filename.endswith(('.geojson', '.json')):
            file_format = 'geojson'
        elif filename.endswith('.csv'):
            file_format = 'csv'
        else:
            return Response(
                {'error': 'Format de fichier non supporté. Utilisez .geojson, .json ou .csv.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Read file content
        try:
            file_content = uploaded_file.read()
            if isinstance(file_content, bytes):
                file_content_str = file_content.decode('utf-8-sig')
            else:
                file_content_str = file_content
        except Exception as e:
            return Response(
                {'error': f'Impossible de lire le fichier: {e}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Parse
        try:
            if file_format == 'geojson':
                parsed = BulkSiteImportService.parse_geojson(file_content_str)
            else:
                parsed = BulkSiteImportService.parse_csv(file_content_str)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Detect properties
        all_properties = set()
        for site_data in parsed:
            all_properties.update(site_data['properties'].keys())
        detected_properties = sorted(all_properties)

        # Field mapping
        field_mapping_str = request.data.get('field_mapping')
        if field_mapping_str:
            import json
            try:
                if isinstance(field_mapping_str, str):
                    field_mapping = json.loads(field_mapping_str)
                else:
                    field_mapping = field_mapping_str
            except (json.JSONDecodeError, ValueError):
                return Response(
                    {'error': 'Le field_mapping JSON est invalide.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            field_mapping = BulkSiteImportService.detect_field_mapping(detected_properties)

        suggested_mapping = BulkSiteImportService.detect_field_mapping(detected_properties)

        # Apply mapping
        mapped = BulkSiteImportService.apply_field_mapping(parsed, field_mapping)

        # Validate
        validated = BulkSiteImportService.validate_batch(mapped)

        # Build response
        sites_response = []
        total_valid = 0
        total_errors = 0
        total_warnings = 0
        total_duplicates = 0

        for site_data in validated:
            has_errors = len(site_data.get('errors', [])) > 0
            has_warnings = len(site_data.get('warnings', [])) > 0
            has_duplicate = site_data.get('duplicate_info') is not None

            if has_errors:
                total_errors += 1
            elif has_duplicate:
                total_duplicates += 1
            else:
                total_valid += 1

            if has_warnings:
                total_warnings += 1

            sites_response.append({
                'row_index': site_data['row_index'],
                'original_properties': site_data['original_properties'],
                'mapped_data': site_data['mapped_data'],
                'geometry': site_data.get('geometry'),
                'has_geometry': site_data.get('has_geometry', False),
                'errors': site_data.get('errors', []),
                'warnings': site_data.get('warnings', []),
                'duplicate_info': site_data.get('duplicate_info'),
                'similar_names': site_data.get('similar_names', []),
            })

        return Response({
            'detected_properties': detected_properties,
            'suggested_mapping': suggested_mapping,
            'applied_mapping': field_mapping,
            'sites': sites_response,
            'total': len(sites_response),
            'valid': total_valid,
            'errors': total_errors,
            'warnings': total_warnings,
            'duplicates': total_duplicates,
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAdminOrganisme],
            url_path='bulk_import_execute')
    def bulk_import_execute(self, request):
        """
        Exécute l'import en masse des sites sélectionnés.
        POST JSON: { sites: [...], selected_indices: [...] }

        Si ≤50 sites: import synchrone.
        Si >50 sites: import asynchrone via Celery, retourne job_id.
        """
        from .services_bulk_import import BulkSiteImportService
        from .models import BulkImportJob

        sites = request.data.get('sites', [])
        selected_indices = request.data.get('selected_indices', [])

        if not sites or not selected_indices:
            return Response(
                {'error': 'Aucun site sélectionné pour l\'import.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        selected_sites = [s for s in sites if s.get('row_index') in selected_indices]

        if len(selected_sites) <= 50:
            # Synchronous import
            result = BulkSiteImportService.import_sites(selected_sites, request.user, selected_indices)
            return Response({
                'async': False,
                **result,
            }, status=status.HTTP_201_CREATED)
        else:
            # Async import via Celery
            job = BulkImportJob.objects.create(
                user=request.user,
                status='pending',
                total_sites=len(selected_sites),
                import_data={
                    'sites': selected_sites,
                    'selected_indices': selected_indices,
                },
            )

            from .tasks import bulk_import_sites_task
            bulk_import_sites_task.delay(job.id)

            return Response({
                'async': True,
                'job_id': job.id,
                'message': f'Import de {len(selected_sites)} sites lancé en arrière-plan.',
            }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrganisme],
            url_path='bulk_import_status')
    def bulk_import_status(self, request):
        """
        Retourne le statut d'un job d'import en masse.
        GET /api/users/sites/bulk_import_status/?job_id=X
        """
        from .models import BulkImportJob

        job_id = request.query_params.get('job_id')
        if not job_id:
            return Response(
                {'error': 'Paramètre job_id requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            job = BulkImportJob.objects.get(id=int(job_id))
        except (BulkImportJob.DoesNotExist, ValueError):
            return Response(
                {'error': 'Job introuvable.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify ownership (super admin can see all)
        if not request.user.is_super_admin() and job.user_id != request.user.pk:
            return Response(
                {'error': 'Accès refusé.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response({
            'job_id': job.id,
            'status': job.status,
            'total_sites': job.total_sites,
            'processed_sites': job.processed_sites,
            'created_sites': job.created_sites,
            'failed_sites': job.failed_sites,
            'validation_pending_sites': job.validation_pending_sites,
            'result_data': job.result_data,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
        })