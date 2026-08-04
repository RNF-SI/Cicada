"""#600 — réglages du tableau de programmation annuelle.

Deux cases à cocher au-dessus du tableau budgétaire, valables dès que le mode
de ventilation intègre le type de budget :

* ``declinaison_par_type_cout`` — affiche (ou non) le détail des coûts
  (salarial / stage / prestataire / autres). Décochée, seules les enveloppes
  fonctionnement et investissement sont saisies à la main.
* ``cout_salarial_auto`` — coût salarial calculé (jours × coût jour) ou saisi.

Les deux sont cochées par défaut. Les actions EXISTANTES en ``by_type`` /
``by_org_type`` ont été saisies en enveloppes : on les bascule à ``False`` pour
que leur tableau continue d'afficher exactement ce qui y a été saisi. Les modes
« + type de poste » gardent ``True`` (ils affichaient déjà le détail).

Le coût salarial saisi manuellement se stocke par année (mode sans organisme)
ou par organisme/année, en fonctionnement et en investissement.
"""

from django.db import migrations, models


def set_legacy_flags(apps, schema_editor):
    Operation = apps.get_model('plans', 'Operation')
    Operation.objects.filter(
        ventilation_mode__in=('by_type', 'by_org_type')
    ).update(declinaison_par_type_cout=False)


def unset_legacy_flags(apps, schema_editor):
    Operation = apps.get_model('plans', 'Operation')
    Operation.objects.filter(
        ventilation_mode__in=('by_type', 'by_org_type')
    ).update(declinaison_par_type_cout=True)


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0124_ra_partage_oo'),
    ]

    operations = [
        migrations.AddField(
            model_name='operation',
            name='declinaison_par_type_cout',
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Détaille le budget en coût salarial / stage / prestataire / "
                    "autres coûts. Décochée, seules les enveloppes fonctionnement "
                    "et investissement sont saisies à la main."
                ),
                verbose_name='Déclinaison par type de coût',
            ),
        ),
        migrations.AddField(
            model_name='operation',
            name='cout_salarial_auto',
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Calcule le coût salarial depuis les jours saisis × le coût "
                    "jour des postes. Décochée, le coût salarial est saisi à la main."
                ),
                verbose_name='Coût salarial calculé automatiquement',
            ),
        ),
        migrations.AddField(
            model_name='operationannee',
            name='cout_salarial',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True,
                verbose_name='Coût salarial saisi — fonctionnement (€)',
            ),
        ),
        migrations.AddField(
            model_name='operationannee',
            name='cout_salarial_invest',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True,
                verbose_name='Coût salarial saisi — investissement (€)',
            ),
        ),
        migrations.AddField(
            model_name='operationanneeorganisme',
            name='cout_salarial',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True,
                verbose_name='Coût salarial saisi — fonctionnement (€)',
            ),
        ),
        migrations.AddField(
            model_name='operationanneeorganisme',
            name='cout_salarial_invest',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True,
                verbose_name='Coût salarial saisi — investissement (€)',
            ),
        ),
        migrations.RunPython(set_legacy_flags, unset_legacy_flags),
    ]
