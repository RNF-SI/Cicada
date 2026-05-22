# #275 — Statut `modifie` : modification ordinaire d'un plan déjà validé.
# #276 — Statut `mi_parcours` : modification déclarée comme évaluation
#         mi-parcours (unique par chaîne plan_parent).
#
# Aucune donnée à migrer : les plans existants conservent leur statut
# actuel ; les nouveaux statuts sont attribués uniquement aux validations
# à venir via l'endpoint change-status.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0066_add_en_revision_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="plangestion",
            name="statut",
            field=models.CharField(
                choices=[
                    ("draft", "Brouillon"),
                    ("valide", "Validé"),
                    ("modifie", "Modifié"),
                    ("mi_parcours", "Modifié à mi-parcours"),
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
