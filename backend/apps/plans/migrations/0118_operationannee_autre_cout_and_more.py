"""
#624 — détail des coûts au niveau de l'ANNÉE (prévisionnel + réalisé).

Le mode de ventilation « par type de budget + type de poste » affiche
désormais la même décomposition que la ventilation maximale (coût salarial
calculé, stage, prestataire, autres coûts, séparés fonctionnement /
investissement), simplement sans déclinaison par organisme gestionnaire.
Ces champs sont le miroir exact de ceux d'``OperationAnneeOrganisme`` /
``RealisationOperationAnneeOrganisme``.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0117_realisationoperationanneeorganisme_cout_stage_realise"),
    ]

    operations = [
        migrations.AddField(
            model_name="operationannee",
            name="autre_cout",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Autre coût — fonctionnement (€)",
            ),
        ),
        migrations.AddField(
            model_name="operationannee",
            name="autre_cout_commentaire",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Commentaire autre coût — fonctionnement",
            ),
        ),
        migrations.AddField(
            model_name="operationannee",
            name="autre_cout_invest",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Autre coût — investissement (€)",
            ),
        ),
        migrations.AddField(
            model_name="operationannee",
            name="autre_cout_invest_commentaire",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Commentaire autre coût — investissement",
            ),
        ),
        migrations.AddField(
            model_name="operationannee",
            name="cout_prestataire",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Coût prestataire — fonctionnement (€)",
            ),
        ),
        migrations.AddField(
            model_name="operationannee",
            name="cout_prestataire_invest",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Coût prestataire — investissement (€)",
            ),
        ),
        migrations.AddField(
            model_name="operationannee",
            name="cout_stage",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Utilisé en mode ventilation 'by_type_poste' (sans organismes)",
                max_digits=12,
                null=True,
                verbose_name="Coût stage (€)",
            ),
        ),
        migrations.AddField(
            model_name="realisationoperationannee",
            name="autre_cout_commentaire_realise",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Commentaire autre coût réalisé — fonctionnement",
            ),
        ),
        migrations.AddField(
            model_name="realisationoperationannee",
            name="autre_cout_invest_commentaire_realise",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Commentaire autre coût réalisé — investissement",
            ),
        ),
        migrations.AddField(
            model_name="realisationoperationannee",
            name="autre_cout_invest_realise",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Autre coût réalisé — investissement (€)",
            ),
        ),
        migrations.AddField(
            model_name="realisationoperationannee",
            name="autre_cout_realise",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Autre coût réalisé — fonctionnement (€)",
            ),
        ),
        migrations.AddField(
            model_name="realisationoperationannee",
            name="cout_prestataire_invest_realise",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Coût prestataire réalisé — investissement (€)",
            ),
        ),
        migrations.AddField(
            model_name="realisationoperationannee",
            name="cout_prestataire_realise",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Coût prestataire réalisé — fonctionnement (€)",
            ),
        ),
        migrations.AddField(
            model_name="realisationoperationannee",
            name="cout_stage_realise",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=12,
                null=True,
                verbose_name="Coût stage réalisé (€)",
            ),
        ),
    ]
