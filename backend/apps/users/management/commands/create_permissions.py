"""
Commande Django pour créer les groupes et permissions par défaut.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.users.models import Role, BibOrganismes, Site, CorRoleSite, CorOgSite


class Command(BaseCommand):
    help = 'Crée les groupes et permissions par défaut pour le système de rôles'

    def handle(self, *args, **options):
        """
        Crée les groupes et permissions.
        """
        self.stdout.write('🔐 Création des groupes et permissions...')
        
        # Définition des permissions personnalisées pour chaque modèle
        permissions_data = [
            # Permissions pour Role (Utilisateurs)
            {
                'model': Role,
                'codename': 'view_all_users',
                'name': 'Peut voir tous les utilisateurs'
            },
            {
                'model': Role,
                'codename': 'manage_organisme_users',
                'name': 'Peut gérer les utilisateurs de son organisme'
            },
            
            # Permissions pour BibOrganismes
            {
                'model': BibOrganismes,
                'codename': 'view_all_organismes',
                'name': 'Peut voir tous les organismes'
            },
            {
                'model': BibOrganismes,
                'codename': 'manage_own_organisme',
                'name': 'Peut gérer son propre organisme'
            },
            
            # Permissions pour Site
            {
                'model': Site,
                'codename': 'view_all_sites',
                'name': 'Peut voir tous les sites'
            },
            {
                'model': Site,
                'codename': 'manage_organisme_sites',
                'name': 'Peut gérer les sites de son organisme'
            },
            {
                'model': Site,
                'codename': 'manage_assigned_sites',
                'name': 'Peut gérer les sites qui lui sont assignés'
            },
            
            # Permissions générales
            {
                'model': Role,
                'codename': 'access_admin_interface',
                'name': 'Peut accéder à l\'interface d\'administration'
            },
            {
                'model': Role,
                'codename': 'export_data',
                'name': 'Peut exporter les données'
            },
            {
                'model': Role,
                'codename': 'import_data',
                'name': 'Peut importer les données'
            },
        ]
        
        # Créer les permissions personnalisées
        created_permissions = {}
        for perm_data in permissions_data:
            content_type = ContentType.objects.get_for_model(perm_data['model'])
            permission, created = Permission.objects.get_or_create(
                codename=perm_data['codename'],
                defaults={
                    'name': perm_data['name'],
                    'content_type': content_type,
                }
            )
            created_permissions[perm_data['codename']] = permission
            
            if created:
                self.stdout.write(f'✅ Permission créée: {perm_data["name"]}')
            else:
                self.stdout.write(f'ℹ️  Permission existe: {perm_data["name"]}')
        
        # Définition des groupes et leurs permissions
        groups_data = [
            {
                'name': 'Super Administrateurs',
                'permissions': [
                    # Toutes les permissions Django par défaut
                    'add_role', 'change_role', 'delete_role', 'view_role',
                    'add_biborganismes', 'change_biborganismes', 'delete_biborganismes', 'view_biborganismes',
                    'add_site', 'change_site', 'delete_site', 'view_site',
                    'add_corrolesite', 'change_corrolesite', 'delete_corrolesite', 'view_corrolesite',
                    'add_corogsite', 'change_corogsite', 'delete_corogsite', 'view_corogsite',
                    # Permissions personnalisées
                    'view_all_users', 'view_all_organismes', 'view_all_sites',
                    'manage_organisme_users', 'manage_own_organisme', 'manage_organisme_sites',
                    'manage_assigned_sites', 'access_admin_interface', 'export_data', 'import_data',
                ]
            },
            {
                'name': 'Rédacteurs Principaux',
                'permissions': [
                    # Mêmes permissions qu'admin organisme + accès global plans
                    'add_role', 'change_role', 'view_role',
                    'view_biborganismes', 'change_biborganismes',
                    'add_site', 'change_site', 'view_site',
                    'add_corrolesite', 'change_corrolesite', 'view_corrolesite',
                    'add_corogsite', 'change_corogsite', 'view_corogsite',
                    # Permissions personnalisées
                    'view_all_users', 'view_all_organismes', 'view_all_sites',
                    'manage_organisme_users', 'manage_own_organisme', 'manage_organisme_sites',
                    'manage_assigned_sites', 'access_admin_interface', 'export_data',
                ]
            },
            {
                'name': 'Administrateurs Organisme',
                'permissions': [
                    # Permissions de base sur les modèles
                    'add_role', 'change_role', 'view_role',
                    'view_biborganismes', 'change_biborganismes',
                    'add_site', 'change_site', 'view_site',
                    'add_corrolesite', 'change_corrolesite', 'view_corrolesite',
                    'add_corogsite', 'change_corogsite', 'view_corogsite',
                    # Permissions personnalisées
                    'manage_organisme_users', 'manage_own_organisme', 'manage_organisme_sites',
                    'access_admin_interface', 'export_data',
                ]
            },
            {
                'name': 'Référents',
                'permissions': [
                    # Permissions de lecture principalement
                    'view_role', 'view_biborganismes', 'view_site',
                    'add_site', 'change_site',
                    'view_corrolesite', 'view_corogsite',
                    # Permissions personnalisées
                    'manage_assigned_sites', 'export_data',
                ]
            },
            {
                'name': 'Utilisateurs',
                'permissions': [
                    # Permissions de lecture uniquement
                    'view_role', 'view_biborganismes', 'view_site',
                    'view_corrolesite', 'view_corogsite',
                ]
            },
        ]
        
        # Créer les groupes et assigner les permissions
        for group_data in groups_data:
            group, created = Group.objects.get_or_create(name=group_data['name'])
            
            if created:
                self.stdout.write(f'✅ Groupe créé: {group_data["name"]}')
            else:
                self.stdout.write(f'ℹ️  Groupe existe: {group_data["name"]}')
            
            # Ajouter les permissions au groupe
            permissions_to_add = []
            for perm_codename in group_data['permissions']:
                try:
                    # Chercher dans les permissions personnalisées d'abord
                    if perm_codename in created_permissions:
                        permission = created_permissions[perm_codename]
                    else:
                        # Chercher dans les permissions Django par défaut
                        permission = Permission.objects.get(codename=perm_codename)
                    permissions_to_add.append(permission)
                except Permission.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  Permission non trouvée: {perm_codename}')
                    )
            
            # Assigner toutes les permissions au groupe
            group.permissions.set(permissions_to_add)
            self.stdout.write(f'   → {len(permissions_to_add)} permissions assignées')
        
        # Mapper les rôles aux groupes
        self.stdout.write('\n👥 Attribution des groupes aux utilisateurs existants...')
        role_group_mapping = {
            'super_admin': 'Super Administrateurs',
            'redacteur_principal': 'Rédacteurs Principaux',
            'admin_og': 'Administrateurs Organisme',
            'referent': 'Référents',
            'utilisateur': 'Utilisateurs',
        }
        
        for role_level, group_name in role_group_mapping.items():
            try:
                group = Group.objects.get(name=group_name)
                users = Role.objects.filter(role_level=role_level)
                
                for user in users:
                    user.groups.add(group)
                
                self.stdout.write(f'✅ {users.count()} utilisateurs ajoutés au groupe "{group_name}"')
                
            except Group.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Groupe non trouvé: {group_name}')
                )
        
        # Attribution automatique du groupe Super Administrateur aux superusers
        superusers = Role.objects.filter(is_superuser=True)
        if superusers.exists():
            super_admin_group = Group.objects.get(name='Super Administrateurs')
            for superuser in superusers:
                superuser.groups.add(super_admin_group)
                # Mettre à jour le role_level si nécessaire
                if superuser.role_level != 'super_admin':
                    superuser.role_level = 'super_admin'
                    superuser.save()
            
            self.stdout.write(f'✅ {superusers.count()} superusers ajoutés au groupe Super Administrateurs')
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 Groupes et permissions créés avec succès!')
        )
        
        # Affichage du résumé
        self.stdout.write('\n📋 Résumé:')
        for group in Group.objects.all():
            perm_count = group.permissions.count()
            user_count = group.user_set.count()
            self.stdout.write(f'   • {group.name}: {perm_count} permissions, {user_count} utilisateurs')