# Generated manually for OperationAnnee and FinanceOperation models

import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_initial"),
        ("plans", "0013_remove_operation_cout_communication_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="OperationAnnee",
            fields=[
                (
                    "id_operation_annee",
                    models.AutoField(primary_key=True, serialize=False),
                ),
                ("annee", models.IntegerField(verbose_name="Année")),
                (
                    "periodicite",
                    models.BooleanField(default=False, verbose_name="Périodicité"),
                ),
                (
                    "budget",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=12,
                        null=True,
                        verbose_name="Budget prévisionnel (€)",
                    ),
                ),
                (
                    "etp",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=8,
                        null=True,
                        verbose_name="Travail prévisionnel (jours)",
                    ),
                ),
                (
                    "periodicite_mensuelle",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Format: {"1": true, "2": false, ..., "12": true}',
                        verbose_name="Périodicité mensuelle",
                    ),
                ),
                (
                    "geom",
                    django.contrib.gis.db.models.fields.GeometryField(
                        blank=True,
                        null=True,
                        srid=4326,
                        verbose_name="Emprise spatiale",
                    ),
                ),
                (
                    "id_operateur",
                    models.ForeignKey(
                        blank=True,
                        db_column="id_operateur",
                        limit_choices_to={"id_type__mnemonique": "OPERATEUR_TYPE"},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="operation_annees_operateur",
                        to="core.nomenclature",
                        verbose_name="Type d'opérateur",
                    ),
                ),
                (
                    "id_operation",
                    models.ForeignKey(
                        db_column="id_operation",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="operation_annees",
                        to="plans.operation",
                        verbose_name="Opération",
                    ),
                ),
            ],
            options={
                "verbose_name": "Année d'opération",
                "verbose_name_plural": "Années d'opération",
                "db_table": '"general"."t_operation_annees"',
                "db_table_comment": "Programmation annuelle des opérations",
                "ordering": ["annee"],
                "unique_together": {("id_operation", "annee")},
            },
        ),
        migrations.CreateModel(
            name="FinanceOperation",
            fields=[
                (
                    "id_finance_operation",
                    models.AutoField(primary_key=True, serialize=False),
                ),
                (
                    "libelle",
                    models.CharField(max_length=255, verbose_name="Libellé"),
                ),
                (
                    "id_categorie",
                    models.ForeignKey(
                        blank=True,
                        db_column="id_categorie",
                        limit_choices_to={"id_type__mnemonique": "CATEGORIE_FINANCE"},
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="finances_categorie",
                        to="core.nomenclature",
                        verbose_name="Catégorie de financement",
                    ),
                ),
                (
                    "id_operation",
                    models.ForeignKey(
                        db_column="id_operation",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="finances",
                        to="plans.operation",
                        verbose_name="Opération",
                    ),
                ),
            ],
            options={
                "verbose_name": "Financement d'opération",
                "verbose_name_plural": "Financements d'opération",
                "db_table": '"general"."t_finances_operations"',
                "db_table_comment": "Sources de financement des opérations",
                "ordering": ["libelle"],
            },
        ),
    ]
