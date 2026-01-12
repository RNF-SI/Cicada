# Generated migration to remove 'referent' role level

from django.db import migrations, models


def migrate_referent_to_utilisateur(apps, schema_editor):
    """
    Migre les utilisateurs avec role_level='referent' vers 'utilisateur'.
    Note: Ces utilisateurs conserveront leurs droits de référent s'ils sont
    assignés comme référent de site ou de plan de gestion.
    """
    Role = apps.get_model('users', 'Role')
    updated = Role.objects.filter(role_level='referent').update(role_level='utilisateur')
    if updated:
        print(f"\n  -> {updated} utilisateur(s) migré(s) de 'referent' vers 'utilisateur'")


def reverse_migration(apps, schema_editor):
    """
    Migration inverse - ne fait rien car on ne peut pas savoir
    quels utilisateurs avaient le role_level='referent'.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_role_deactivated_at_role_deactivated_by_and_more'),
    ]

    operations = [
        # D'abord migrer les données
        migrations.RunPython(migrate_referent_to_utilisateur, reverse_migration),
        # Puis modifier le champ pour retirer l'option 'referent'
        migrations.AlterField(
            model_name='role',
            name='role_level',
            field=models.CharField(
                choices=[
                    ('utilisateur', 'Utilisateur'),
                    ('admin_og', 'Administrateur Organisme'),
                    ('super_admin', 'Super Administrateur'),
                ],
                default='utilisateur',
                max_length=20,
                verbose_name='Niveau de rôle',
            ),
        ),
    ]
