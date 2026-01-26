"""
Seeder pour les groupes Django.
"""
from typing import Any, Dict, List

from django.contrib.auth.models import Group, Permission

from .base import BaseSeeder


class GroupsSeeder(BaseSeeder):
    """
    Cree les groupes Django pour les permissions.

    Groupes:
    - Super Administrateurs
    - Administrateurs Organisme
    - Referents
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
            'name': 'Referents',
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
        Cree les groupes Django.

        Returns:
            Dict avec les groupes crees (nom -> groupe)
        """
        self.log_header('Creation des groupes')

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
                self.log_item('cree', group.name)
            else:
                self.log_item('existant', group.name)
            groups[group.name] = group

        self.log('  Groupes crees', 'SUCCESS')
        self.context.set('groups', groups)
        return groups

    def reset(self) -> int:
        """
        Les groupes ne sont pas supprimes car ils sont necessaires a l'application.

        Returns:
            0 (aucun groupe supprime)
        """
        return 0

    def get_dry_run_summary(self) -> List[str]:
        """
        Resume des groupes qui seraient crees.

        Returns:
            Liste des lignes du resume
        """
        return [
            '\nGroupes Django:',
            '  - Super Administrateurs',
            '  - Administrateurs Organisme',
            '  - Referents',
            '  - Utilisateurs',
        ]
