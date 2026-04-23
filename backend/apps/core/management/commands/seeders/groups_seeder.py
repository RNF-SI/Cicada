"""
Seeder pour les groupes Django.
"""
from typing import Any, Dict, List

from django.contrib.auth.models import Group, Permission

from .base import BaseSeeder


class GroupsSeeder(BaseSeeder):
    """
    Crée les groupes Django pour les permissions.

    Groupes:
    - Super Administrateurs
    - Administrateurs Organisme
    - Référents
    - Utilisateurs
    """

    name = 'groups'
    dependencies = []

    GROUPS_DATA = [
        {
            'name': 'Super Administrateurs',
            'permissions': [
                'add_role', 'change_role', 'delete_role', 'view_role',
                'add_site', 'change_site', 'delete_site', 'view_site',
                'add_plangestion', 'change_plangestion', 'delete_plangestion', 'view_plangestion',
                'add_biborganismes', 'change_biborganismes', 'delete_biborganismes', 'view_biborganismes'
            ]
        },
        {
            'name': 'Administrateurs Organisme',
            'permissions': [
                'change_role', 'view_role',
                'add_site', 'change_site', 'view_site',
                'add_plangestion', 'change_plangestion', 'view_plangestion',
                'view_biborganismes'
            ]
        },
        {
            'name': 'Référents',
            'permissions': [
                'view_role',
                'change_site', 'view_site',
                'add_plangestion', 'change_plangestion', 'view_plangestion'
            ]
        },
        {
            'name': 'Utilisateurs',
            'permissions': ['view_site', 'view_plangestion']
        },
    ]

    def seed(self) -> Dict[str, Group]:
        """
        Crée les groupes Django.

        Returns:
            Dict avec les groupes créés (nom -> groupe)
        """
        self.log_header('Création des groupes')

        # Migrer l'ancien nom sans accent vers le nom canonique accentué.
        old_referents = Group.objects.filter(name='Referents').first()
        new_referents = Group.objects.filter(name='Référents').first()
        if old_referents and not new_referents:
            old_referents.name = 'Référents'
            old_referents.save(update_fields=['name'])
            self.log_item('renommé', "Referents → Référents")
        elif old_referents and new_referents:
            # Les deux existent : reporter les utilisateurs de l'ancien vers le
            # nouveau groupe puis supprimer l'ancien.
            from apps.users.models import Role
            for user in Role.objects.filter(groups=old_referents):
                user.groups.add(new_referents)
            old_referents.delete()
            self.log_item('fusionné', "Referents → Référents")

        groups = {}
        for group_data in self.GROUPS_DATA:
            group, created = Group.objects.get_or_create(name=group_data['name'])
            if created:
                for perm_codename in group_data['permissions']:
                    try:
                        perm = Permission.objects.get(codename=perm_codename)
                        group.permissions.add(perm)
                    except Permission.DoesNotExist:
                        pass
                self.log_item('créé', group.name)
            else:
                self.log_item('existant', group.name)
            groups[group.name] = group

        self.log('  Groupes créés', 'SUCCESS')
        self.context.set('groups', groups)
        return groups

    def reset(self) -> int:
        """
        Les groupes ne sont pas supprimés car ils sont nécessaires à l'application.

        Returns:
            0 (aucun groupe supprimé)
        """
        return 0

    def get_dry_run_summary(self) -> List[str]:
        """
        Résumé des groupes qui seraient créés.

        Returns:
            Liste des lignes du résumé
        """
        return [
            '\nGroupes Django:',
            '  - Super Administrateurs',
            '  - Administrateurs Organisme',
            '  - Référents',
            '  - Utilisateurs',
        ]
