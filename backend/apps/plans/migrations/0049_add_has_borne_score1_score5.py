"""Add has_borne_score1 and has_borne_score5 to persist optional extreme bound state."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0048_add_metrique_direction_inclusivity"),
    ]

    operations = [
        migrations.AddField(
            model_name="metrique",
            name="has_borne_score1",
            field=models.BooleanField(
                default=False,
                help_text="Croissant: borne inf score 1 active. Décroissant: borne sup score 1 active.",
                verbose_name="Borne extrême score 1 active",
            ),
        ),
        migrations.AddField(
            model_name="metrique",
            name="has_borne_score5",
            field=models.BooleanField(
                default=False,
                help_text="Croissant: borne sup score 5 active. Décroissant: borne inf score 5 active.",
                verbose_name="Borne extrême score 5 active",
            ),
        ),
    ]
