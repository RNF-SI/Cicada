"""
Migration pour ajouter le rôle 'redacteur_principal' dans ROLE_CHOICES.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_add_cor_redacteur_plan'),
    ]

    operations = [
        migrations.AlterField(
            model_name='role',
            name='role_level',
            field=models.CharField(
                choices=[
                    ('utilisateur', 'Utilisateur'),
                    ('admin_og', 'Administrateur Organisme'),
                    ('redacteur_principal', 'Rédacteur Principal'),
                    ('super_admin', 'Super Administrateur'),
                ],
                default='utilisateur',
                max_length=20,
                verbose_name='Niveau de rôle',
            ),
        ),
    ]
