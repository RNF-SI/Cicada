from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("search", "0009_retrait_hub"),
    ]

    operations = [
        migrations.AddField(
            model_name="raccordementhub",
            name="jetons_saisis",
            field=models.BooleanField(default=False, verbose_name="Jetons saisis manuellement"),
        ),
        migrations.AddField(
            model_name="raccordementhub",
            name="exploration_source",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "Selon la configuration du serveur"),
                    ("local", "Index local"),
                    ("hub", "Hub d'exploration"),
                ],
                default="",
                max_length=10,
                verbose_name="Source de l'exploration",
            ),
        ),
    ]
