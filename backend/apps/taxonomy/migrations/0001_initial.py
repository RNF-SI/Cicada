"""
Migration initiale pour le schéma taxonomie (TaxRef).

Crée le schema PostgreSQL, les tables et les extensions nécessaires.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        # Créer le schema et les extensions
        migrations.RunSQL(
            sql=[
                'CREATE SCHEMA IF NOT EXISTS taxonomie;',
                'CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public;',
                'CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA public;',
            ],
            reverse_sql=[
                # Ne pas supprimer le schema en reverse pour éviter
                # la perte de données accidentelle
            ],
        ),
        # Table des rangs taxonomiques
        migrations.CreateModel(
            name='BibTaxrefRang',
            fields=[
                ('id_rang', models.CharField(
                    max_length=10, primary_key=True, serialize=False,
                    verbose_name='Code rang')),
                ('nom_rang', models.CharField(
                    max_length=100, verbose_name='Nom du rang')),
                ('tri_rang', models.IntegerField(
                    blank=True, null=True, verbose_name='Ordre de tri')),
            ],
            options={
                'db_table': '"taxonomie"."bib_taxref_rangs"',
                'managed': True,
                'verbose_name': 'Rang taxonomique',
                'verbose_name_plural': 'Rangs taxonomiques',
            },
        ),
        # Table des types d'habitats
        migrations.CreateModel(
            name='BibTaxrefHabitat',
            fields=[
                ('id_habitat', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name="Code habitat")),
                ('nom_habitat', models.CharField(
                    max_length=255,
                    verbose_name="Nom de l'habitat")),
            ],
            options={
                'db_table': '"taxonomie"."bib_taxref_habitats"',
                'managed': True,
                'verbose_name': "Type d'habitat TaxRef",
                'verbose_name_plural': "Types d'habitats TaxRef",
            },
        ),
        # Table des statuts taxonomiques
        migrations.CreateModel(
            name='BibTaxrefStatut',
            fields=[
                ('id_statut', models.CharField(
                    max_length=50, primary_key=True, serialize=False,
                    verbose_name='Code statut')),
                ('nom_statut', models.CharField(
                    max_length=255, verbose_name='Nom du statut')),
            ],
            options={
                'db_table': '"taxonomie"."bib_taxref_statuts"',
                'managed': True,
                'verbose_name': 'Statut taxonomique',
                'verbose_name_plural': 'Statuts taxonomiques',
            },
        ),
        # Table principale TaxRef
        migrations.CreateModel(
            name='Taxref',
            fields=[
                ('cd_nom', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name='Code nom')),
                ('id_statut', models.CharField(
                    blank=True, db_index=True, max_length=50, null=True,
                    verbose_name='Statut')),
                ('id_habitat', models.IntegerField(
                    blank=True, null=True, verbose_name='Habitat')),
                ('id_rang', models.CharField(
                    blank=True, db_index=True, max_length=10, null=True,
                    verbose_name='Rang')),
                ('regne', models.CharField(
                    blank=True, db_index=True, max_length=50, null=True,
                    verbose_name='Règne')),
                ('phylum', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Phylum')),
                ('classe', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Classe')),
                ('ordre', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Ordre')),
                ('famille', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Famille')),
                ('sous_famille', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Sous-famille')),
                ('tribu', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Tribu')),
                ('cd_taxsup', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Code taxon supérieur')),
                ('cd_sup', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Code supérieur')),
                ('cd_ref', models.IntegerField(
                    blank=True, db_index=True, null=True,
                    verbose_name='Code référence')),
                ('lb_nom', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Nom latin')),
                ('lb_auteur', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Auteur')),
                ('nom_complet', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Nom complet')),
                ('nom_complet_html', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Nom complet HTML')),
                ('nom_valide', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Nom valide')),
                ('nom_vern', models.TextField(
                    blank=True, null=True,
                    verbose_name='Nom vernaculaire')),
                ('nom_vern_eng', models.TextField(
                    blank=True, null=True,
                    verbose_name='Nom vernaculaire anglais')),
                ('group1_inpn', models.CharField(
                    blank=True, max_length=100, null=True,
                    verbose_name='Groupe 1 INPN')),
                ('group2_inpn', models.CharField(
                    blank=True, db_index=True, max_length=100, null=True,
                    verbose_name='Groupe 2 INPN')),
                ('group3_inpn', models.CharField(
                    blank=True, max_length=100, null=True,
                    verbose_name='Groupe 3 INPN')),
                ('url', models.TextField(
                    blank=True, null=True,
                    verbose_name='URL fiche INPN')),
            ],
            options={
                'db_table': '"taxonomie"."taxref"',
                'managed': True,
                'verbose_name': 'Taxon (TaxRef)',
                'verbose_name_plural': 'Taxons (TaxRef)',
            },
        ),
        # Table de métadonnées / versioning
        migrations.CreateModel(
            name='TMetaTaxref',
            fields=[
                ('id', models.AutoField(
                    primary_key=True, serialize=False)),
                ('referential_name', models.CharField(
                    max_length=100,
                    verbose_name='Nom du référentiel')),
                ('version', models.CharField(
                    max_length=50, verbose_name='Version')),
                ('update_date', models.DateTimeField(
                    auto_now=True,
                    verbose_name='Date de mise à jour')),
            ],
            options={
                'db_table': '"taxonomie"."t_meta_taxref"',
                'managed': True,
                'verbose_name': 'Métadonnée TaxRef',
                'verbose_name_plural': 'Métadonnées TaxRef',
            },
        ),
    ]
