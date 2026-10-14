# #700 — Rôle « Rédacteur externe » (bureau d'étude…)

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0010_change_redacteur_general_label"),
    ]

    operations = [
        migrations.AlterField(
            model_name="role",
            name="role_level",
            field=models.CharField(
                choices=[
                    ("utilisateur", "Utilisateur"),
                    ("redacteur", "Rédacteur externe"),
                    ("admin_og", "Administrateur Organisme"),
                    ("redacteur_principal", "Rédacteur Général"),
                    ("super_admin", "Super Administrateur"),
                ],
                default="utilisateur",
                max_length=20,
                verbose_name="Niveau de rôle",
            ),
        ),
    ]
