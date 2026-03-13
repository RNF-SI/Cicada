"""
Migration initiale pour le schéma ref_campanule (CAMPanule).

Crée le schema PostgreSQL et les tables pour le catalogue des
méthodes et protocoles de collecte de données naturalistes.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        # Créer le schema
        migrations.RunSQL(
            sql=[
                'CREATE SCHEMA IF NOT EXISTS ref_campanule;',
            ],
            reverse_sql=[],
        ),

        # ======== Tables principales ========

        migrations.CreateModel(
            name='CampanuleProtocole',
            fields=[
                ('cd_protocole', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name='Code protocole')),
                ('lb_protocole_court', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Libellé court')),
                ('cd_prot_metier', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Code métier')),
                ('code_v0_9', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Code v0.9')),
                ('cd_prot_ref', models.IntegerField(
                    blank=True, db_index=True, null=True,
                    verbose_name='Code protocole de référence')),
                ('lb_protocole_complet', models.TextField(
                    blank=True, null=True,
                    verbose_name='Libellé complet')),
                ('lb_protocole_en', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Libellé anglais')),
                ('date_publi', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date de publication')),
                ('version', models.CharField(
                    blank=True, max_length=100, null=True,
                    verbose_name='Version')),
                ('obsolete', models.CharField(
                    blank=True, max_length=10, null=True,
                    verbose_name='Obsolète')),
                ('prot_auteur', models.TextField(
                    blank=True, null=True,
                    verbose_name='Auteur(s)')),
                ('url_perm', models.TextField(
                    blank=True, null=True,
                    verbose_name='URL permanente')),
                ('url', models.TextField(
                    blank=True, null=True,
                    verbose_name='URL')),
                ('url_complementaire', models.TextField(
                    blank=True, null=True,
                    verbose_name='URL complémentaire')),
                ('description', models.TextField(
                    blank=True, null=True,
                    verbose_name='Description')),
                ('descr_cible_prot', models.TextField(
                    blank=True, null=True,
                    verbose_name='Description cible')),
                ('descr_objectif_prot', models.TextField(
                    blank=True, null=True,
                    verbose_name='Description objectif')),
                ('cible', models.CharField(
                    blank=True, db_index=True, max_length=255, null=True,
                    verbose_name='Cible principale')),
                ('echelle_restit', models.CharField(
                    blank=True, max_length=100, null=True,
                    verbose_name='Échelle de restitution')),
                ('saisie', models.TextField(
                    blank=True, null=True,
                    verbose_name='Interface de saisie')),
                ('biologie', models.TextField(
                    blank=True, null=True,
                    verbose_name='Paramètres biologiques')),
                ('abiotique', models.TextField(
                    blank=True, null=True,
                    verbose_name='Paramètres abiotiques')),
                ('nature_donnees', models.TextField(
                    blank=True, null=True,
                    verbose_name='Nature des données')),
                ('analyse_reference', models.TextField(
                    blank=True, null=True,
                    verbose_name="Référence d'analyse")),
                ('guide_sinp_donnees', models.TextField(
                    blank=True, null=True,
                    verbose_name='Guide SINP données')),
                ('norme', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Norme')),
                ('indicateur', models.TextField(
                    blank=True, null=True,
                    verbose_name='Indicateur')),
                ('categorie_prot', models.CharField(
                    blank=True, db_index=True, max_length=255, null=True,
                    verbose_name='Catégorie')),
                ('uuid', models.CharField(
                    blank=True, max_length=36, null=True, unique=True,
                    verbose_name='UUID')),
                ('gele', models.CharField(
                    blank=True, max_length=10, null=True,
                    verbose_name='Gelé')),
            ],
            options={
                'db_table': '"ref_campanule"."protocoles"',
                'managed': True,
                'verbose_name': 'Protocole CAMPanule',
                'verbose_name_plural': 'Protocoles CAMPanule',
            },
        ),

        migrations.CreateModel(
            name='CampanuleMethode',
            fields=[
                ('cd_methode', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name='Code méthode')),
                ('cd_meth_metier', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Code métier')),
                ('lb_methode_court', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Libellé court')),
                ('lb_methode_complet', models.TextField(
                    blank=True, null=True,
                    verbose_name='Libellé complet')),
                ('lb_methode_en', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Libellé anglais')),
                ('url_perm', models.TextField(
                    blank=True, null=True,
                    verbose_name='URL permanente')),
                ('url_complementaire', models.TextField(
                    blank=True, null=True,
                    verbose_name='URL complémentaire')),
                ('descr_methode', models.TextField(
                    blank=True, null=True,
                    verbose_name='Description')),
                ('exemples_cible_meth', models.TextField(
                    blank=True, null=True,
                    verbose_name='Exemples de cibles')),
                ('descr_objectif_meth', models.TextField(
                    blank=True, null=True,
                    verbose_name='Description objectif')),
                ('nature_donnees', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Nature des données')),
                ('analyse_reference', models.TextField(
                    blank=True, null=True,
                    verbose_name="Référence d'analyse")),
                ('uuid', models.CharField(
                    blank=True, max_length=36, null=True, unique=True,
                    verbose_name='UUID')),
                ('gele', models.CharField(
                    blank=True, max_length=10, null=True,
                    verbose_name='Gelé')),
            ],
            options={
                'db_table': '"ref_campanule"."methodes"',
                'managed': True,
                'verbose_name': 'Méthode CAMPanule',
                'verbose_name_plural': 'Méthodes CAMPanule',
            },
        ),

        migrations.CreateModel(
            name='CampanuleTechnique',
            fields=[
                ('cd_technique', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name='Code technique')),
                ('lb_technique_fr', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Libellé français')),
                ('niveau', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Niveau hiérarchique')),
                ('cd_tech_metier', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Code métier')),
                ('cd_tech_sup', models.IntegerField(
                    blank=True, db_index=True, null=True,
                    verbose_name='Code technique supérieure')),
                ('lb_tech_complet_fr', models.TextField(
                    blank=True, null=True,
                    verbose_name='Libellé complet français')),
                ('lb_technique_en', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Libellé anglais')),
                ('categorie_tech', models.CharField(
                    blank=True, db_index=True, max_length=255, null=True,
                    verbose_name='Catégorie')),
                ('cible', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Cible principale')),
                ('descr_technique', models.TextField(
                    blank=True, null=True,
                    verbose_name='Description')),
                ('descr_cible_tech', models.TextField(
                    blank=True, null=True,
                    verbose_name='Description cible')),
                ('active', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Active/Passive')),
                ('derangement', models.CharField(
                    blank=True, max_length=100, null=True,
                    verbose_name='Dérangement')),
                ('prelevement', models.CharField(
                    blank=True, max_length=100, null=True,
                    verbose_name='Prélèvement')),
                ('comm_collecte', models.TextField(
                    blank=True, null=True,
                    verbose_name='Commentaire collecte')),
                ('corresp_occtax', models.TextField(
                    blank=True, null=True,
                    verbose_name='Correspondance OccTax')),
                ('corresp_soh', models.TextField(
                    blank=True, null=True,
                    verbose_name='Correspondance SOH')),
                ('tag_tax', models.CharField(
                    blank=True, max_length=10, null=True,
                    verbose_name='Tag taxons')),
                ('tag_hab', models.CharField(
                    blank=True, max_length=10, null=True,
                    verbose_name='Tag habitats')),
                ('uuid', models.CharField(
                    blank=True, max_length=36, null=True, unique=True,
                    verbose_name='UUID')),
                ('gele', models.CharField(
                    blank=True, max_length=10, null=True,
                    verbose_name='Gelé')),
            ],
            options={
                'db_table': '"ref_campanule"."techniques"',
                'managed': True,
                'verbose_name': 'Technique CAMPanule',
                'verbose_name_plural': 'Techniques CAMPanule',
            },
        ),

        # ======== Tables complémentaires ========

        migrations.CreateModel(
            name='CampanuleAttribut',
            fields=[
                ('cd_attribut', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name='Code attribut')),
                ('lb_attribut', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Libellé')),
                ('categorie_attribut', models.CharField(
                    blank=True, db_index=True, max_length=100, null=True,
                    verbose_name='Catégorie')),
            ],
            options={
                'db_table': '"ref_campanule"."attributs"',
                'managed': True,
                'verbose_name': 'Attribut CAMPanule',
                'verbose_name_plural': 'Attributs CAMPanule',
            },
        ),

        migrations.CreateModel(
            name='CampanuleProtEchantillonnage',
            fields=[
                ('cd_prot_echantillonnage', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name='Code échantillonnage')),
                ('cd_protocole', models.IntegerField(
                    db_index=True,
                    verbose_name='Code protocole')),
                ('unite', models.TextField(
                    blank=True, null=True,
                    verbose_name="Unité d'échantillonnage")),
                ('nb_unite', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name="Nombre d'unités")),
                ('duree', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Durée')),
                ('taille', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Taille')),
                ('passages_an', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Passages par an')),
                ('periode_an', models.TextField(
                    blank=True, null=True,
                    verbose_name="Période de l'année")),
                ('plan_ech', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name="Plan d'échantillonnage")),
                ('commentaire', models.TextField(
                    blank=True, null=True,
                    verbose_name='Commentaire')),
                ('niveau', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name="Niveau d'emboîtement")),
            ],
            options={
                'db_table': '"ref_campanule"."prot_echantillonnage"',
                'managed': True,
                'verbose_name': 'Échantillonnage protocole',
                'verbose_name_plural': 'Échantillonnages protocoles',
            },
        ),

        migrations.CreateModel(
            name='CampanuleDocsWeb',
            fields=[
                ('cd_doc', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name='Code document')),
                ('reference', models.TextField(
                    blank=True, null=True,
                    verbose_name='Référence bibliographique')),
            ],
            options={
                'db_table': '"ref_campanule"."docs_web"',
                'managed': True,
                'verbose_name': 'Document CAMPanule',
                'verbose_name_plural': 'Documents CAMPanule',
            },
        ),

        # ======== Tables de correspondance ========

        migrations.CreateModel(
            name='CampanuleProtAttributsRel',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False,
                    verbose_name='ID')),
                ('cd_protocole', models.IntegerField(
                    db_index=True, verbose_name='Code protocole')),
                ('cd_attribut', models.IntegerField(
                    db_index=True, verbose_name='Code attribut')),
            ],
            options={
                'db_table': '"ref_campanule"."prot_attributs_rel"',
                'managed': True,
                'verbose_name': 'Relation protocole-attribut',
                'verbose_name_plural': 'Relations protocole-attribut',
                'unique_together': {('cd_protocole', 'cd_attribut')},
            },
        ),

        migrations.CreateModel(
            name='CampanuleProtBiblioRel',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False,
                    verbose_name='ID')),
                ('cd_protocole', models.IntegerField(
                    db_index=True, verbose_name='Code protocole')),
                ('cd_doc', models.IntegerField(
                    db_index=True, verbose_name='Code document')),
                ('page', models.CharField(
                    blank=True, max_length=100, null=True,
                    verbose_name='Page')),
            ],
            options={
                'db_table': '"ref_campanule"."prot_biblio_rel"',
                'managed': True,
                'verbose_name': 'Relation protocole-document',
                'verbose_name_plural': 'Relations protocole-document',
            },
        ),

        migrations.CreateModel(
            name='CampanuleProtMethRel',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False,
                    verbose_name='ID')),
                ('cd_protocole', models.IntegerField(
                    db_index=True, verbose_name='Code protocole')),
                ('cd_methode', models.IntegerField(
                    db_index=True, verbose_name='Code méthode')),
                ('commentaire', models.TextField(
                    blank=True, null=True,
                    verbose_name='Commentaire')),
            ],
            options={
                'db_table': '"ref_campanule"."prot_meth_rel"',
                'managed': True,
                'verbose_name': 'Relation protocole-méthode',
                'verbose_name_plural': 'Relations protocole-méthode',
            },
        ),

        migrations.CreateModel(
            name='CampanuleProtTechRel',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False,
                    verbose_name='ID')),
                ('cd_protocole', models.IntegerField(
                    db_index=True, verbose_name='Code protocole')),
                ('cd_technique', models.IntegerField(
                    db_index=True, verbose_name='Code technique')),
                ('commentaire', models.TextField(
                    blank=True, null=True,
                    verbose_name='Commentaire')),
            ],
            options={
                'db_table': '"ref_campanule"."prot_tech_rel"',
                'managed': True,
                'verbose_name': 'Relation protocole-technique',
                'verbose_name_plural': 'Relations protocole-technique',
            },
        ),

        migrations.CreateModel(
            name='CampanuleMethAttributsRel',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False,
                    verbose_name='ID')),
                ('cd_methode', models.IntegerField(
                    db_index=True, verbose_name='Code méthode')),
                ('cd_attribut', models.IntegerField(
                    db_index=True, verbose_name='Code attribut')),
            ],
            options={
                'db_table': '"ref_campanule"."meth_attributs_rel"',
                'managed': True,
                'verbose_name': 'Relation méthode-attribut',
                'verbose_name_plural': 'Relations méthode-attribut',
                'unique_together': {('cd_methode', 'cd_attribut')},
            },
        ),

        migrations.CreateModel(
            name='CampanuleMethBiblioRel',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False,
                    verbose_name='ID')),
                ('cd_methode', models.IntegerField(
                    db_index=True, verbose_name='Code méthode')),
                ('cd_doc', models.IntegerField(
                    db_index=True, verbose_name='Code document')),
                ('page', models.CharField(
                    blank=True, max_length=100, null=True,
                    verbose_name='Page')),
            ],
            options={
                'db_table': '"ref_campanule"."meth_biblio_rel"',
                'managed': True,
                'verbose_name': 'Relation méthode-document',
                'verbose_name_plural': 'Relations méthode-document',
            },
        ),

        migrations.CreateModel(
            name='CampanuleTechAttributsRel',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False,
                    verbose_name='ID')),
                ('cd_technique', models.IntegerField(
                    db_index=True, verbose_name='Code technique')),
                ('cd_attribut', models.IntegerField(
                    db_index=True, verbose_name='Code attribut')),
            ],
            options={
                'db_table': '"ref_campanule"."tech_attributs_rel"',
                'managed': True,
                'verbose_name': 'Relation technique-attribut',
                'verbose_name_plural': 'Relations technique-attribut',
                'unique_together': {('cd_technique', 'cd_attribut')},
            },
        ),

        migrations.CreateModel(
            name='CampanuleTechBiblioRel',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True, primary_key=True, serialize=False,
                    verbose_name='ID')),
                ('cd_technique', models.IntegerField(
                    db_index=True, verbose_name='Code technique')),
                ('cd_doc', models.IntegerField(
                    db_index=True, verbose_name='Code document')),
                ('page', models.CharField(
                    blank=True, max_length=100, null=True,
                    verbose_name='Page')),
            ],
            options={
                'db_table': '"ref_campanule"."tech_biblio_rel"',
                'managed': True,
                'verbose_name': 'Relation technique-document',
                'verbose_name_plural': 'Relations technique-document',
            },
        ),

        # ======== Table d'autocomplete ========

        migrations.CreateModel(
            name='AutocompleteProtocole',
            fields=[
                ('cd_protocole', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name='Code protocole')),
                ('search_name', models.TextField(
                    verbose_name='Nom de recherche')),
                ('lb_protocole_court', models.CharField(
                    blank=True, max_length=500, null=True,
                    verbose_name='Libellé court')),
                ('lb_protocole_complet', models.TextField(
                    blank=True, null=True,
                    verbose_name='Libellé complet')),
                ('description', models.TextField(
                    blank=True, null=True,
                    verbose_name='Description')),
                ('cible', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Cible')),
                ('categorie_prot', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Catégorie')),
                ('prot_auteur', models.TextField(
                    blank=True, null=True,
                    verbose_name='Auteur(s)')),
                ('obsolete', models.CharField(
                    blank=True, max_length=10, null=True,
                    verbose_name='Obsolète')),
            ],
            options={
                'db_table': '"ref_campanule"."autocomplete_protocole"',
                'managed': True,
                'verbose_name': 'Autocomplete protocole',
                'verbose_name_plural': 'Autocomplete protocoles',
            },
        ),
    ]
