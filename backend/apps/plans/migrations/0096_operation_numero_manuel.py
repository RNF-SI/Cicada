# Generated for #485 — numéro manuel dans le code d'affichage des actions
# (décline #442 / #526).

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0095_enjeu_numero_manuel"),
    ]

    operations = [
        migrations.AddField(
            model_name="operation",
            name="numero_manuel",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text="Numéro fixé manuellement dans le code (laisser vide pour la numérotation automatique)",
                verbose_name="Numéro fixé manuellement",
            ),
        ),
    ]
