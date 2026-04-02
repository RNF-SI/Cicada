"""Add direction (sens_variation) and boundary inclusivity fields to Metrique.

Issue #134: Pour les métriques à intervalle, permettre de définir
le sens de variation (croissant/décroissant) et l'inclusivité
de chaque frontière entre niveaux de score.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0047_add_ventilation_mode_to_operation"),
    ]

    operations = [
        migrations.AddField(
            model_name="metrique",
            name="sens_variation",
            field=models.CharField(
                choices=[("CROISSANT", "Croissant"), ("DECROISSANT", "Décroissant")],
                default="CROISSANT",
                help_text="Croissant = plus c'est haut mieux c'est, Décroissant = plus c'est bas mieux c'est",
                max_length=20,
                verbose_name="Sens de variation",
            ),
        ),
        migrations.AddField(
            model_name="metrique",
            name="score_1_sup_inclusive",
            field=models.BooleanField(
                default=True,
                help_text="True: score 1 ≤ seuil, score 2 > seuil. False: score 1 < seuil, score 2 ≥ seuil",
                verbose_name="Borne sup score 1 inclusive",
            ),
        ),
        migrations.AddField(
            model_name="metrique",
            name="score_2_sup_inclusive",
            field=models.BooleanField(
                default=True,
                verbose_name="Borne sup score 2 inclusive",
            ),
        ),
        migrations.AddField(
            model_name="metrique",
            name="score_3_sup_inclusive",
            field=models.BooleanField(
                default=True,
                verbose_name="Borne sup score 3 inclusive",
            ),
        ),
        migrations.AddField(
            model_name="metrique",
            name="score_4_sup_inclusive",
            field=models.BooleanField(
                default=True,
                verbose_name="Borne sup score 4 inclusive",
            ),
        ),
    ]
