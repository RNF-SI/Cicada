"""
Seeder pour les modules applicatifs.
"""
from typing import Any, List

from apps.core.models import Module

from .base import BaseSeeder


class ModulesSeeder(BaseSeeder):
    """
    Cree les modules applicatifs de l'application.

    Les modules sont:
    - plans: Mes plans de gestion
    - sites: Mes sites
    - inventaires: Mes inventaires et suivis
    - zonages: Zonages reglementaires (requires_access=True)
    """

    name = 'modules'
    dependencies = []

    # Donnees des modules
    MODULES_DATA = [
        {
            'code': 'plans',
            'name': 'Mes plans de gestion',
            'description': 'Gestion des plans de gestion des espaces naturels',
            'icon': 'fi-rr-document',
            'color': 'primary',
            'route': '/plans',
            'requires_access': False,
            'is_active': True,
            'display_order': 0,
        },
        {
            'code': 'sites',
            'name': 'Mes sites',
            'description': 'Gestion des sites et espaces proteges',
            'icon': 'fi-rr-map-marker',
            'color': 'salmon',
            'route': '/sites',
            'requires_access': False,
            'is_active': True,
            'display_order': 1,
        },
        {
            'code': 'inventaires',
            'name': 'Mes inventaires et suivis',
            'description': 'Gestion des inventaires et suivis naturalistes',
            'icon': 'fi-rr-test-tube',
            'color': 'yellow',
            'route': '/inventaires',
            'requires_access': False,
            'is_active': True,
            'display_order': 2,
        },
        {
            'code': 'zonages',
            'name': 'Zonages reglementaires',
            'description': 'Acces aux zonages reglementaires et leur gestion',
            'icon': 'fi-rr-map',
            'color': 'terra-cotta',
            'route': '/zonages',
            'requires_access': True,
            'is_active': True,
            'display_order': 3,
        },
    ]

    def seed(self) -> List[Module]:
        """
        Cree les modules applicatifs.

        Returns:
            Liste des modules crees
        """
        self.log_header('Creation des modules')

        modules = []
        for module_data in self.MODULES_DATA:
            module, created = Module.objects.get_or_create(
                code=module_data['code'],
                defaults=module_data
            )
            modules.append(module)

            status = "cree" if created else "existant"
            self.log_item(status, f"{module.code}: {module.name}")

        self.log_summary(len(modules), 'modules')
        self.context.set('modules', modules)
        return modules

    def reset(self) -> int:
        """
        Les modules ne sont pas supprimes car ils sont necessaires a l'application.

        Returns:
            0 (aucun module supprime)
        """
        return 0

    def get_dry_run_summary(self) -> List[str]:
        """
        Resume des modules qui seraient crees.

        Returns:
            Liste des lignes du resume
        """
        return [
            '\nModules (4):',
            '  - plans: Mes plans de gestion (primary)',
            '  - sites: Mes sites (salmon)',
            '  - inventaires: Mes inventaires et suivis (yellow)',
            '  - zonages: Zonages reglementaires (terra-cotta) [requires_access]',
        ]
