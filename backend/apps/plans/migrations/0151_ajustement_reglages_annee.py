from django.db import migrations, models


class Migration(migrations.Migration):
    """#794 (retour 13/11) — réglages de saisie propres à une année ajustée.

    Nouveaux champs nuls : les ajustements existants gardent les réglages de
    leur action. Rien à reprendre."""

    dependencies = [
        ('plans', '0150_appariements_types_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='ajustementannuel', name='declinaison_par_type_cout',
            field=models.BooleanField(
                blank=True, null=True, verbose_name="Déclinaison par type de coût (année)"),
        ),
        migrations.AddField(
            model_name='ajustementannuel', name='cout_salarial_auto',
            field=models.BooleanField(
                blank=True, null=True,
                verbose_name="Coût salarial calculé automatiquement (année)"),
        ),
        migrations.AddField(
            model_name='ajustementannuel', name='declinaison_par_poste',
            field=models.BooleanField(
                blank=True, null=True, verbose_name="Déclinaison par type de poste (année)"),
        ),
    ]
