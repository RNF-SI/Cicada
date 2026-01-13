# Generated manually for module access feature

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0003_remove_requester_name_cache"),
    ]

    operations = [
        # Ajouter le champ target_module
        migrations.AddField(
            model_name="validationrequest",
            name="target_module",
            field=models.CharField(
                blank=True,
                help_text="Code du module demandé (ex: zonages)",
                max_length=50,
                null=True,
                verbose_name="Module cible",
            ),
        ),
        # Mettre à jour les choix de request_type pour inclure module_access
        migrations.AlterField(
            model_name="validationrequest",
            name="request_type",
            field=models.CharField(
                choices=[
                    ("user_registration", "Inscription utilisateur"),
                    ("site_access", "Accès à un site"),
                    ("plan_access", "Accès à un plan de gestion"),
                    ("module_access", "Accès à un module"),
                    ("admin_deactivation", "Désactivation admin_og"),
                    ("referent_validation", "Validation référent site"),
                ],
                db_index=True,
                max_length=30,
                verbose_name="Type de demande",
            ),
        ),
    ]
