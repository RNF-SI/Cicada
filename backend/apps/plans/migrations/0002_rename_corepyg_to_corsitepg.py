# Generated manually for renaming CorEpPg to CorSitePg

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0001_initial'),
    ]

    operations = [
        # Renommer la table
        migrations.RunSQL(
            "ALTER TABLE cor_ep_pg RENAME TO cor_site_pg;",
            reverse_sql="ALTER TABLE cor_site_pg RENAME TO cor_ep_pg;"
        ),
        
        # Renommer le modèle dans Django
        migrations.RenameModel(
            old_name='CorEpPg',
            new_name='CorSitePg',
        ),
        
        # La relation sera mise à jour automatiquement via le RenameModel
    ]