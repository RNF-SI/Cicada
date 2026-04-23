"""
Seeder pour les modules applicatifs.
"""
from typing import Any, List

from apps.core.models import Module

from .base import BaseSeeder


class ModulesSeeder(BaseSeeder):
    """
    Crée les modules applicatifs de l'application.

    Les modules sont:
    - plans: Mes plans de gestion
    - sites: Mes sites
    - inventaires: Mes inventaires et suivis
    - zonages: Zonages réglementaires (requires_access=True)
    """

    name = 'modules'
    dependencies = []

    # Données des modules
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
            'description': 'Gestion des sites et espaces protégés',
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
            'name': 'Zonages réglementaires',
            'description': 'Accès aux zonages réglementaires et leur gestion',
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
        Crée les modules applicatifs.

        Returns:
            Liste des modules créés
        """
        self.log_header('Création des modules')

        modules = []
        for module_data in self.MODULES_DATA:
            module, created = Module.objects.get_or_create(
                code=module_data['code'],
                defaults=module_data
            )
            modules.append(module)

            status = "créé" if created else "existant"
            self.log_item(status, f"{module.code}: {module.name}")

        self.log_summary(len(modules), 'modules')
        self.context.set('modules', modules)
        return modules

    def reset(self) -> int:
        """
        Les modules ne sont pas supprimés car ils sont nécessaires à l'application.

        Returns:
            0 (aucun module supprimé)
        """
        return 0

    def get_dry_run_summary(self) -> List[str]:
        """
        Résumé des modules qui seraient créés.

        Returns:
            Liste des lignes du résumé
        """
        return [
            '\nModules (4):',
            '  - plans: Mes plans de gestion (primary)',
            '  - sites: Mes sites (salmon)',
            '  - inventaires: Mes inventaires et suivis (yellow)',
            '  - zonages: Zonages réglementaires (terra-cotta) [requires_access]',
        ]
