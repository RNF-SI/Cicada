# Migration: Add standalone fields to SuiviInventaire and Protocole

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0017_protocole'),
        ('core', '0002_initial'),
    ]

    operations = [
        # --- Protocole new fields ---
        migrations.AddField(
            model_name='protocole',
            name='nom_protocole',
            field=models.CharField(
                blank=True, default='', max_length=255,
                help_text='Nom du protocole (si non Campanule)',
                verbose_name='Nom du protocole',
            ),
        ),
        migrations.AddField(
            model_name='protocole',
            name='mode_validation',
            field=models.CharField(
                blank=True, default='', max_length=500,
                help_text='Mode et champ de validation du protocole',
                verbose_name='Mode et champ de validation',
            ),
        ),
        # --- SuiviInventaire new fields ---
        migrations.AddField(
            model_name='suiviinventaire',
            name='intitule',
            field=models.CharField(
                blank=True, default='', max_length=500,
                help_text='Nom affiché dans la liste des suivis/inventaires',
                verbose_name='Intitulé',
            ),
        ),
        migrations.AddField(
            model_name='suiviinventaire',
            name='prix_indicatif',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True,
                help_text='Prix indicatif en euros par an',
                verbose_name='Prix indicatif (€/an)',
            ),
        ),
        migrations.AddField(
            model_name='suiviinventaire',
            name='id_type_suivi',
            field=models.ForeignKey(
                blank=True, null=True,
                db_column='id_type_suivi',
                help_text='Type : Suivi, Inventaire, ou Suivi et inventaire',
                limit_choices_to={'id_type__mnemonique': 'TYPE_SUIVI'},
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='suivis_type',
                to='core.nomenclature',
                verbose_name='Type de suivi',
            ),
        ),
        migrations.AddField(
            model_name='suiviinventaire',
            name='integre_plan_gestion',
            field=models.BooleanField(
                blank=True, null=True,
                help_text='Ce suivi est-il intégré dans un plan de gestion ?',
                verbose_name='Intégré dans un plan de gestion',
            ),
        ),
        migrations.AddField(
            model_name='suiviinventaire',
            name='id_pg',
            field=models.ForeignKey(
                blank=True, null=True,
                db_column='id_pg',
                help_text='Plan de gestion associé (optionnel)',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='suivis_inventaires',
                to='plans.plangestion',
                verbose_name='Plan de gestion lié',
            ),
        ),
        migrations.AddField(
            model_name='suiviinventaire',
            name='cible_secondaire',
            field=models.CharField(
                blank=True, default='', max_length=255,
                help_text='Cible secondaire du suivi/inventaire',
                verbose_name='Cible secondaire',
            ),
        ),
        migrations.AddField(
            model_name='suiviinventaire',
            name='habitat_ref',
            field=models.CharField(
                blank=True, default='', max_length=500,
                help_text='Référentiel habitat associé',
                verbose_name='Référentiel habitat',
            ),
        ),
        migrations.AddField(
            model_name='suiviinventaire',
            name='id_statut',
            field=models.ForeignKey(
                blank=True, null=True,
                db_column='id_statut',
                help_text='Statut du suivi (En cours, Terminé, A venir)',
                limit_choices_to={'id_type__mnemonique': 'STATUT_SUIVI'},
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='suivis_statut',
                to='core.nomenclature',
                verbose_name='Statut',
            ),
        ),
        migrations.AddField(
            model_name='suiviinventaire',
            name='actif',
            field=models.BooleanField(
                default=True,
                help_text='Suivi actif ou inactif',
                verbose_name='Actif',
            ),
        ),
        migrations.AddField(
            model_name='suiviinventaire',
            name='annee_fin_suivi',
            field=models.IntegerField(
                blank=True, null=True,
                help_text='Année de fin du suivi',
                verbose_name='Année de fin du suivi',
            ),
        ),
        migrations.AddField(
            model_name='suiviinventaire',
            name='frequence_nombre',
            field=models.IntegerField(
                blank=True, null=True,
                help_text='Nombre de répétitions',
                verbose_name='Fréquence (nombre)',
            ),
        ),
        migrations.AddField(
            model_name='suiviinventaire',
            name='frequence_unite',
            field=models.CharField(
                blank=True, max_length=50, null=True,
                help_text='Unité de fréquence (jour, semaine, mois, an)',
                verbose_name='Fréquence (unité)',
            ),
        ),
        migrations.AddField(
            model_name='suiviinventaire',
            name='commentaires',
            field=models.TextField(
                blank=True, default='',
                help_text='Détails et commentaires',
                verbose_name='Commentaires',
            ),
        ),
    ]
