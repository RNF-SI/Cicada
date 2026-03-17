"""
Remplacer les M2M Operation↔Indicateur et Operation↔Metrique
par une FK simple Operation.id_metrique → Metrique.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0031_oo_remove_id_enjeu"),
    ]

    operations = [
        # 1. Remove M2M fields from Operation first
        migrations.RemoveField(
            model_name="operation",
            name="indicateurs",
        ),
        migrations.RemoveField(
            model_name="operation",
            name="metriques",
        ),

        # 2. Delete the through tables
        migrations.DeleteModel(
            name="CorOperationIndicateur",
        ),
        migrations.DeleteModel(
            name="CorOperationMetrique",
        ),

        # 3. Add FK id_metrique to Operation
        migrations.AddField(
            model_name="operation",
            name="id_metrique",
            field=models.ForeignKey(
                blank=True,
                db_column="id_metrique",
                help_text="Métrique associée à cette opération",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="operations",
                to="plans.metrique",
                verbose_name="Métrique",
            ),
        ),

        # 4. Update table comments
        migrations.AlterModelTableComment(
            name="etatactuel",
            table_comment="États actuels des enjeux",
        ),
        migrations.AlterModelTableComment(
            name="objectiflongterme",
            table_comment="Objectifs à long terme des états actuels",
        ),
        migrations.AlterModelTableComment(
            name="objectifoperationnel",
            table_comment="Objectifs opérationnels des facteurs d'influence",
        ),
    ]
