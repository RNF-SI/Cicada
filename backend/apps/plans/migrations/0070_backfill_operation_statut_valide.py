"""
Data migration #251 — Backfill statut='valide' pour les opérations existantes.

Contexte : la migration 0068_operation_statut a ajouté le champ `statut` avec
`default='draft'`, ce qui a marqué *toutes* les opérations existantes comme
brouillon. Or, avant #251, il n'y avait pas de notion de brouillon : ces
opérations étaient toutes considérées comme validées.

Cette migration :
  1. Repasse à `'valide'` toutes les opérations actuellement à `'draft'`
     (rattrape le backfill de 0068).
  2. Aligne le default du champ sur `'valide'` côté schéma pour rester
     cohérent avec le modèle.
"""
from django.db import migrations, models


def backfill_operations_to_valide(apps, schema_editor):
    Operation = apps.get_model('plans', 'Operation')
    Operation.objects.filter(statut='draft').update(statut='valide')


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0069_csrpn_workflow"),
    ]

    operations = [
        migrations.RunPython(
            backfill_operations_to_valide,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="operation",
            name="statut",
            field=models.CharField(
                choices=[("draft", "Brouillon"), ("valide", "Validé")],
                db_index=True,
                default="valide",
                help_text="Brouillon tant que l'action n'a pas été validée explicitement",
                max_length=10,
                verbose_name="Statut",
            ),
        ),
    ]
