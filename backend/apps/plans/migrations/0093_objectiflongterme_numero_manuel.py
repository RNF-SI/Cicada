# Generated for #442 — numéro manuel des OLT

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0092_mesure_valeurs_blocs_alter_mesure_valeur"),
    ]

    operations = [
        migrations.AddField(
            model_name="objectiflongterme",
            name="numero_manuel",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text="Numéro global fixé manuellement (laisser vide pour la numérotation automatique)",
                verbose_name="Numéro fixé manuellement",
            ),
        ),
    ]
