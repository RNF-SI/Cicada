"""#645 — Interrupteur de l'API publique des métadonnées des plans."""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_siteconfiguration_federation_partage'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteconfiguration',
            name='api_publique_plans',
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Ouvre une API en lecture seule et sans authentification exposant "
                    "les métadonnées des plans de gestion (hors brouillons) : nom, "
                    "période, rang, rédacteurs, dates de validation, sites. Le contenu "
                    "des plans n'est jamais exposé. Destinée aux applications tierces "
                    "de gestion documentaire."
                ),
                verbose_name='API publique des métadonnées des plans',
            ),
        ),
    ]
