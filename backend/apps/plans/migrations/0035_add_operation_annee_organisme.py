"""
Migration: Add OperationAnneeOrganisme table for per-organisme budget/work tracking.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0034_oo_remove_id_facteur_influence'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OperationAnneeOrganisme',
            fields=[
                ('id_operation_annee_organisme', models.AutoField(primary_key=True, serialize=False)),
                ('budget_fonctionnement', models.DecimalField(
                    blank=True, decimal_places=2, max_digits=12,
                    null=True, verbose_name='Budget fonctionnement (€)'
                )),
                ('budget_investissement', models.DecimalField(
                    blank=True, decimal_places=2, max_digits=12,
                    null=True, verbose_name='Budget investissement (€)'
                )),
                ('etp', models.DecimalField(
                    blank=True, decimal_places=2, max_digits=8,
                    null=True, verbose_name='Travail prévisionnel (jours)'
                )),
                ('id_operation_annee', models.ForeignKey(
                    db_column='id_operation_annee',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='organismes',
                    to='plans.operationannee',
                    verbose_name="Année d'opération",
                )),
                ('id_organisme', models.ForeignKey(
                    db_column='id_organisme',
                    on_delete=django.db.models.deletion.CASCADE,
                    to='users.biborganismes',
                    verbose_name='Organisme',
                )),
            ],
            options={
                'verbose_name': "Organisme - Année d'opération",
                'verbose_name_plural': "Organismes - Années d'opération",
                'db_table': '"general"."t_operation_annee_organismes"',
                'db_table_comment': 'Ventilation budget/travail par organisme et par année',
                'ordering': ['id_organisme__nom_organisme'],
                'unique_together': {('id_operation_annee', 'id_organisme')},
            },
        ),
    ]
