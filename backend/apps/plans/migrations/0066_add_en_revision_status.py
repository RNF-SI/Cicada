# #278 — Statut "en cours de révision" : plan validé en fin de cycle dont la
# période est dépassée mais qui reste utilisé pendant la rédaction du plan de
# rang suivant. Verrouillé en lecture seule (comme `valide`).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0065_renumber_versions_to_integers"),
    ]

    operations = [
        migrations.AlterField(
            model_name="plangestion",
            name="statut",
            field=models.CharField(
                choices=[
                    ("draft", "Brouillon"),
                    ("valide", "Validé"),
                    ("etendu", "Étendu"),
                    ("en_revision", "En cours de révision"),
                    ("archive", "Archivé"),
                ],
                default="draft",
                max_length=20,
                verbose_name="Statut",
            ),
        ),
    ]
