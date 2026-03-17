"""
Migration: Make id_pression non-null and remove id_facteur_influence from OO.

Step 2 of 2: After data migration populated id_pression, enforce NOT NULL
and drop the old id_facteur_influence column.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0033_oo_add_id_pression'),
    ]

    operations = [
        # 1. Make id_pression NOT NULL
        migrations.AlterField(
            model_name='objectifoperationnel',
            name='id_pression',
            field=models.ForeignKey(
                db_column='id_pression',
                help_text="Pression parente de cet objectif opérationnel",
                on_delete=django.db.models.deletion.CASCADE,
                related_name='objectifs_operationnels',
                to='plans.pression',
                verbose_name='Pression',
            ),
        ),
        # 2. Remove old id_facteur_influence FK
        migrations.RemoveField(
            model_name='objectifoperationnel',
            name='id_facteur_influence',
        ),
    ]
