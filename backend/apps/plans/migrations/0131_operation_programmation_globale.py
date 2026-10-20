"""#735 — programmation globale + déclinaison par type de coût pour tous les modes.

* ``Operation.programmation_globale`` : budget et temps de travail saisis une
  fois pour la période de l'action, sur une ligne ``OperationAnnee`` sans année
  (une seule par action). Les actions existantes restent « annuelles ».
* La case « déclinaison par type de coût » s'ouvre aux modes ``none`` et
  ``by_org``. Elle valait ``True`` par défaut sans être proposée : les actions
  EXISTANTES de ces modes ont été saisies en totaux, on la passe à ``False``
  pour que leur tableau affiche exactement ce qui y a été saisi.
"""

import django.db.models.manager
from django.db import migrations, models


def set_legacy_flags(apps, schema_editor):
    Operation = apps.get_model('plans', 'Operation')
    Operation.objects.filter(
        ventilation_mode__in=('none', 'by_org')
    ).update(declinaison_par_type_cout=False)


def unset_legacy_flags(apps, schema_editor):
    Operation = apps.get_model('plans', 'Operation')
    Operation.objects.filter(
        ventilation_mode__in=('none', 'by_org')
    ).update(declinaison_par_type_cout=True)


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0130_protocole_ordre_saisie"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="operationannee",
            options={
                "base_manager_name": "tous",
                "ordering": ["annee"],
                "verbose_name": "Année d'opération",
                "verbose_name_plural": "Années d'opération",
            },
        ),
        migrations.AlterModelManagers(
            name="operationannee",
            managers=[
                ("objects", django.db.models.manager.Manager()),
                ("tous", django.db.models.manager.Manager()),
            ],
        ),
        migrations.AddField(
            model_name="operation",
            name="programmation_globale",
            field=models.BooleanField(
                default=False,
                help_text="Budget et temps de travail saisis globalement sur la période de l'action plutôt que par année.",
                verbose_name="Programmation globale sur la période",
            ),
        ),
        migrations.AlterField(
            model_name="operationannee",
            name="annee",
            field=models.IntegerField(blank=True, null=True, verbose_name="Année"),
        ),
        migrations.AddConstraint(
            model_name="operationannee",
            constraint=models.UniqueConstraint(
                condition=models.Q(("annee__isnull", True)),
                fields=("id_operation",),
                name="uniq_operation_annee_globale",
            ),
        ),
        migrations.RunPython(set_legacy_flags, unset_legacy_flags),
    ]
