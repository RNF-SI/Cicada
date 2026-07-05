# Generated for #526 — numéro manuel des Enjeux/FCR (décline #442)

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0094_objectifoperationnel_numero_manuel"),
    ]

    operations = [
        migrations.AddField(
            model_name="enjeu",
            name="numero_manuel",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text="Numéro fixé manuellement (laisser vide pour la numérotation automatique)",
                verbose_name="Numéro fixé manuellement",
            ),
        ),
    ]
