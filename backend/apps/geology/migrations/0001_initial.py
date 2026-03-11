"""
Migration initiale pour le schéma ref_inpg (INPG).

Crée le schema PostgreSQL et la table inpg.
"""

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        # Créer le schema
        migrations.RunSQL(
            sql=[
                'CREATE SCHEMA IF NOT EXISTS ref_inpg;',
            ],
            reverse_sql=[],
        ),
        # Table principale INPG
        migrations.CreateModel(
            name='Inpg',
            fields=[
                ('id_inpg', models.IntegerField(
                    primary_key=True, serialize=False,
                    verbose_name='ID INPG')),
                ('geom', django.contrib.gis.db.models.fields.MultiPolygonField(
                    blank=True, null=True, srid=4326,
                    verbose_name='Géométrie')),
                ('id_metier', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='ID métier')),
                ('surface', models.CharField(
                    blank=True, max_length=100, null=True,
                    verbose_name='Surface')),
                ('lb_site', models.TextField(
                    blank=True, null=True,
                    verbose_name='Nom du site')),
                ('typologie_1', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Typologie 1')),
                ('typologie_2', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Typologie 2')),
                ('typologie_3', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Typologie 3')),
                ('accessibilite_1', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Accessibilité 1')),
                ('accessibilite_2', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Accessibilité 2')),
                ('region', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Région')),
                ('departements', models.TextField(
                    blank=True, null=True,
                    verbose_name='Départements')),
                ('communes', models.TextField(
                    blank=True, null=True,
                    verbose_name='Communes')),
                ('niveau_de_diffusion', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Niveau de diffusion')),
                ('organismes_contacts', models.TextField(
                    blank=True, null=True,
                    verbose_name='Organismes contacts')),
                ('superficie_saisie', models.FloatField(
                    blank=True, null=True,
                    verbose_name='Superficie saisie')),
                ('justification_de_superficie', models.TextField(
                    blank=True, null=True,
                    verbose_name='Justification de superficie')),
                ('unite_de_superficie', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Unité de superficie')),
                ('etat_de_conservation', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='État de conservation')),
                ('presentation_succinte', models.TextField(
                    blank=True, null=True,
                    verbose_name='Présentation succincte')),
                ('description_physique', models.TextField(
                    blank=True, null=True,
                    verbose_name='Description physique')),
                ('description_geologique', models.TextField(
                    blank=True, null=True,
                    verbose_name='Description géologique')),
                ('itineraire_dacces', models.TextField(
                    blank=True, null=True,
                    verbose_name="Itinéraire d'accès")),
                ('code_gilges', models.TextField(
                    blank=True, null=True,
                    verbose_name='Code GILGES')),
                ('phenomene_geologique', models.TextField(
                    blank=True, null=True,
                    verbose_name='Phénomène géologique')),
                ('interet_geol_principal', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Intérêt géologique principal')),
                ('justification_interet_geologique_principal', models.TextField(
                    blank=True, null=True,
                    verbose_name='Justification intérêt géologique principal')),
                ('interets_geologiques_secondaires', models.TextField(
                    blank=True, null=True,
                    verbose_name='Intérêts géologiques secondaires')),
                ('interets_geologiques_secondaires_avec_justification', models.TextField(
                    blank=True, null=True,
                    verbose_name='Intérêts géologiques secondaires avec justification')),
                ('interets_pedagogiques', models.TextField(
                    blank=True, null=True,
                    verbose_name='Intérêts pédagogiques')),
                ('justification_interets_pedagogiques', models.TextField(
                    blank=True, null=True,
                    verbose_name='Justification intérêts pédagogiques')),
                ('interets_annexes', models.TextField(
                    blank=True, null=True,
                    verbose_name='Intérêts annexes')),
                ('interets_annexes_avec_justification', models.TextField(
                    blank=True, null=True,
                    verbose_name='Intérêts annexes avec justification')),
                ('interet_histoire_sciences_geologiques', models.TextField(
                    blank=True, null=True,
                    verbose_name='Intérêt histoire sciences géologiques')),
                ('rarete', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Rareté')),
                ('informateurs', models.TextField(
                    blank=True, null=True,
                    verbose_name='Informateurs')),
                ('stratigraphie_age_le_plus_ancien_du_phenomene', models.TextField(
                    blank=True, db_column='stratigraphie__ge_le_plus_ancien_du_phenomene',
                    null=True,
                    verbose_name='Stratigraphie âge le plus ancien du phénomène')),
                ('stratigraphie_age_le_plus_recent_du_phenomene', models.TextField(
                    blank=True, db_column='stratigraphie__ge_le_plus_recent_du_phenomene',
                    null=True,
                    verbose_name='Stratigraphie âge le plus récent du phénomène')),
                ('stratigraphie_age_le_plus_ancien_du_terrain', models.TextField(
                    blank=True, db_column='stratigraphie__ge_le_plus_ancien_du_terrain',
                    null=True,
                    verbose_name='Stratigraphie âge le plus ancien du terrain')),
                ('stratigraphie_age_le_plus_recent_du_terrain', models.TextField(
                    blank=True, db_column='stratigraphie__ge_le_plus_recent_du_terrain',
                    null=True,
                    verbose_name='Stratigraphie âge le plus récent du terrain')),
                ('commentaire_sur_levaluation_du_site', models.TextField(
                    blank=True, null=True,
                    verbose_name="Commentaire sur l'évaluation du site")),
                ('vulnerabilite_naturelle', models.TextField(
                    blank=True, null=True,
                    verbose_name='Vulnérabilité naturelle')),
                ('menace_anthropique', models.TextField(
                    blank=True, null=True,
                    verbose_name='Menace anthropique')),
                ('commentaire_besoin_de_protection', models.TextField(
                    blank=True, null=True,
                    verbose_name='Commentaire besoin de protection')),
                ('commentaire_general_sur_les_menaces', models.TextField(
                    blank=True, null=True,
                    verbose_name='Commentaire général sur les menaces')),
                ('note_geologique_principale', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Note géologique principale')),
                ('note_geologique_secondaire', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Note géologique secondaire')),
                ('note_pedagogique', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Note pédagogique')),
                ('note_histoire_des_sciences', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Note histoire des sciences')),
                ('note_rarete', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Note rareté')),
                ('note_etat_conservation', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Note état conservation')),
                ('note_interet_patrimonial', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Note intérêt patrimonial')),
                ('nombre_etoiles', models.IntegerField(
                    blank=True, null=True,
                    verbose_name="Nombre d'étoiles")),
                ('note_vulnerabilite_naturelle', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Note vulnérabilité naturelle')),
                ('note_menace_anthropique', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Note menace anthropique')),
                ('note_protection_effective', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Note protection effective')),
                ('note_besoin_de_protection', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Note besoin de protection')),
                ('lieudit', models.TextField(
                    blank=True, null=True,
                    verbose_name='Lieu-dit')),
                ('nombre_de_documentations', models.IntegerField(
                    blank=True, null=True,
                    verbose_name='Nombre de documentations')),
                ('legendes_figures', models.TextField(
                    blank=True, null=True,
                    verbose_name='Légendes figures')),
                ('cartes_geologiques_associees', models.TextField(
                    blank=True, null=True,
                    verbose_name='Cartes géologiques associées')),
                ('cartes_ign_associees', models.TextField(
                    blank=True, null=True,
                    verbose_name='Cartes IGN associées')),
                ('cartes_marines_associees', models.TextField(
                    blank=True, null=True,
                    verbose_name='Cartes marines associées')),
                ('zonages_de_reference', models.TextField(
                    blank=True, null=True,
                    verbose_name='Zonages de référence')),
                ('bibliographies_associees', models.TextField(
                    blank=True, null=True,
                    verbose_name='Bibliographies associées')),
                ('collections_associees', models.TextField(
                    blank=True, null=True,
                    verbose_name='Collections associées')),
                ('associations_avec_dautres_sites', models.TextField(
                    blank=True, null=True,
                    verbose_name="Associations avec d'autres sites")),
                ('date_de_premiere_visite', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date de première visite')),
                ('date_de_derniere_visite', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date de dernière visite')),
                ('date_creation_du_site', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date création du site')),
                ('statut_actuel_de_la_fiche', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Statut actuel de la fiche')),
                ('ancien_statut_de_la_fiche', models.CharField(
                    blank=True, max_length=255, null=True,
                    verbose_name='Ancien statut de la fiche')),
                ('statut_de_validation_metier', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Statut validation métier')),
                ('statut_de_validation_crpg', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Statut validation CRPG')),
                ('statut_de_validation_regionale', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Statut validation régionale')),
                ('statut_de_validation_nationale', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Statut validation nationale')),
                ('statut_de_dept_sig', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Statut dept SIG')),
                ('statut_de_validation_sig', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Statut validation SIG')),
                ('statut_de_diffusion_inpn', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Statut diffusion INPN')),
                ('derniere_date_de_modification_de_la_fiche', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Dernière date de modification')),
                ('date_de_validation_metier', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date validation métier')),
                ('date_de_validation_crpg_actuelle', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date validation CRPG actuelle')),
                ('date_de_premiere_validation_regionale', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date première validation régionale')),
                ('date_de_validation_regionale_actuelle', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date validation régionale actuelle')),
                ('date_de_premiere_validation_nationale', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date première validation nationale')),
                ('date_de_validation_nationale_actuelle', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date validation nationale actuelle')),
                ('date_de_premiere_diffusion', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date première diffusion')),
                ('date_de_diffusion_actuelle', models.CharField(
                    blank=True, max_length=50, null=True,
                    verbose_name='Date diffusion actuelle')),
            ],
            options={
                'db_table': '"ref_inpg"."inpg"',
                'managed': True,
                'verbose_name': 'Site géologique INPG',
                'verbose_name_plural': 'Sites géologiques INPG',
                'ordering': ['id_inpg'],
            },
        ),
    ]
