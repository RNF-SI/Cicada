"""
Migration: Remove FK id_pression from ObjectifOperationnel.

Step 2 of 2: Now that the M2M junction table cor_oo_pression is populated,
remove the old FK column and add the M2M field declaration.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0050_oo_m2m_pressions'),
    ]

    operations = [
        # 1. Remove the old FK field
        migrations.RemoveField(
            model_name='objectifoperationnel',
            name='id_pression',
        ),

        # 2. Add the M2M field declaration (uses the existing through table)
        migrations.AddField(
            model_name='objectifoperationnel',
            name='pressions',
            field=models.ManyToManyField(
                blank=True,
                help_text='Pressions liées à cet objectif opérationnel',
                related_name='objectifs_operationnels',
                through='plans.CorOoPression',
                to='plans.pression',
                verbose_name='Pressions',
            ),
        ),

        # 3. Update table comment
        migrations.AlterModelTableComment(
            name='objectifoperationnel',
            table_comment='Objectifs opérationnels liés à des pressions',
        ),
    ]
