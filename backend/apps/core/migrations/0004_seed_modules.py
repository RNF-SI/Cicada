# Data migration to seed initial modules

from django.db import migrations


def seed_modules(apps, schema_editor):
    """
    Cree les modules initiaux de l'application.
    """
    Module = apps.get_model('core', 'Module')

    # Modules de base (accessibles a tous les utilisateurs connectes)
    modules = [
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
        # Modules necessitant un acces specifique
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

    for module_data in modules:
        Module.objects.get_or_create(
            code=module_data['code'],
            defaults=module_data
        )


def remove_modules(apps, schema_editor):
    """
    Supprime les modules crees par cette migration.
    """
    Module = apps.get_model('core', 'Module')
    Module.objects.filter(code__in=['plans', 'sites', 'inventaires', 'zonages']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_add_module_model'),
    ]

    operations = [
        migrations.RunPython(seed_modules, remove_modules),
    ]
