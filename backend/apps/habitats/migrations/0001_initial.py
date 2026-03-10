"""
Migration initiale pour le schéma ref_habitats (HabRef).

Crée le schema PostgreSQL et les tables.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        # Créer le schema et les extensions
        migrations.RunSQL(
            sql=[
                'CREATE SCHEMA IF NOT EXISTS ref_habitats;',
                'CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public;',
                'CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA public;',
            ],
            reverse_sql=[],
        ),
        # Typologies d'habitats
        migrations.CreateModel(
            name='Typoref',
            fields=[
                ('cd_typo', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name='Code typologie')),
                ('cd_table', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Code table')),
                ('lb_typo', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Libellé typologie')),
                ('nom_jeu_donnees', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Nom du jeu de données')),
                ('date_creation', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date de création')),
                ('date_mise_jour', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date de mise à jour')),
                ('auteur_jeu_donnees', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Auteur')),
                ('territoire', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Territoire')),
            ],
            options={
                'db_table': '"ref_habitats"."typoref"',
                'managed': True,
                'verbose_name': "Typologie d'habitats",
                'verbose_name_plural': "Typologies d'habitats",
            },
        ),
        # Table principale HabRef
        migrations.CreateModel(
            name='Habref',
            fields=[
                ('cd_hab', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name='Code habitat')),
                ('fg_validite', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Flag validité')),
                ('cd_typo', models.IntegerField(
                    blank=True, db_index=True, null=True,
                    verbose_name='Code typologie')),
                ('lb_code', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Code label')),
                ('lb_hab_fr', models.CharField(
                    blank=True, max_length=1000, null=True,
                    verbose_name='Nom français')),
                ('lb_hab_fr_complet', models.TextField(
                    blank=True, null=True,
                    verbose_name='Nom français complet')),
                ('lb_hab_en', models.CharField(
                    blank=True, max_length=1000, null=True,
                    verbose_name='Nom anglais')),
                ('lb_auteur', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Auteur')),
                ('niveau', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Niveau hiérarchique')),
                ('lb_description', models.TextField(
                    blank=True, null=True,
                    verbose_name='Description')),
                ('cd_hab_sup', models.IntegerField(
                    blank=True, db_index=True, null=True,
                    verbose_name='Code habitat supérieur')),
                ('path_cd_hab', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Chemin hiérarchique')),
                ('cd_corresp_encours', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Correspondance en cours')),
                ('date_creation', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date de création')),
                ('date_maj', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date de mise à jour')),
            ],
            options={
                'db_table': '"ref_habitats"."habref"',
                'managed': True,
                'verbose_name': 'Habitat (HabRef)',
                'verbose_name_plural': 'Habitats (HabRef)',
            },
        ),
        # Correspondances entre habitats
        migrations.CreateModel(
            name='HabrefCorrespHab',
            fields=[
                ('id', models.AutoField(
                    primary_key=True, serialize=False)),
                ('cd_hab', models.IntegerField(
                    db_index=True, verbose_name='Code habitat')),
                ('cd_hab_entre', models.IntegerField(
                    blank=True, db_index=True, null=True,
                    verbose_name='Code habitat correspondant')),
                ('cd_typo_entre', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Code typologie correspondante')),
                ('lb_code_entre', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Code label correspondant')),
                ('lb_hab_entre', models.CharField(
                    blank=True, max_length=1000, null=True,
                    verbose_name='Nom habitat correspondant')),
                ('niveau_entre', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Niveau correspondant')),
                ('type_rel', models.CharField(
                    blank=True, max_length=100, null=True,
                    verbose_name='Type de relation')),
            ],
            options={
                'db_table': '"ref_habitats"."habref_corresp_hab"',
                'managed': True,
                'verbose_name': 'Correspondance habitat',
                'verbose_name_plural': 'Correspondances habitats',
            },
        ),
        # Correspondances habitat-taxon
        migrations.CreateModel(
            name='HabrefCorrespTaxon',
            fields=[
                ('id', models.AutoField(
                    primary_key=True, serialize=False)),
                ('cd_hab', models.IntegerField(
                    db_index=True, verbose_name='Code habitat')),
                ('cd_nom', models.IntegerField(
                    db_index=True, verbose_name='Code nom taxon')),
                ('nom_cite', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Nom cité')),
            ],
            options={
                'db_table': '"ref_habitats"."habref_corresp_taxon"',
                'managed': True,
                'verbose_name': 'Correspondance habitat-taxon',
                'verbose_name_plural': 'Correspondances habitats-taxons',
            },
        ),
        # Table d'autocomplete
        migrations.CreateModel(
            name='AutocompleteHabitat',
            fields=[
                ('cd_hab', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name='Code habitat')),
                ('cd_typo', models.IntegerField(
                    blank=True, db_index=True, null=True,
                    verbose_name='Code typologie')),
                ('lb_code', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Code label')),
                ('search_name', models.TextField(
                    verbose_name='Nom de recherche')),
                ('lb_hab_fr', models.CharField(
                    blank=True, max_length=1000, null=True,
                    verbose_name='Nom français')),
                ('lb_hab_fr_complet', models.TextField(
                    blank=True, null=True,
                    verbose_name='Nom français complet')),
                ('lb_typo', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Libellé typologie')),
                ('niveau', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Niveau hiérarchique')),
            ],
            options={
                'db_table': '"ref_habitats"."autocomplete_habitat"',
                'managed': True,
                'verbose_name': 'Autocomplete habitat',
                'verbose_name_plural': 'Autocomplete habitats',
            },
        ),
    ]
