from django.db import migrations, models
import django.db.models.deletion

SEED_AND_MAP_SQL = """INSERT INTO ref_nomenclatures.bib_nomenclatures_types (id_type, mnemonique, label, definition, source, statut, date_ajout, date_maj)
VALUES (68, 'TYPE_OBJET_GEOLOGIQUE', 'Type d''objet géologique', 'Typologie des objets géologiques d''un enjeu (in situ / ex situ / documents)', 'CICADA/PatriNat', 'Validé', NOW(), NOW())
ON CONFLICT (id_type) DO NOTHING;

INSERT INTO ref_nomenclatures.t_nomenclatures
    (id_nomenclature, id_type, cd_nomenclature, mnemonique, label, definition, source, statut, hierarchy, actif)
VALUES
        (1601, 68, 'IS_SITE_PALEO', 'IS_SITE_PALEO', 'Site paléontologique', 'Site paléontologique', 'CICADA/PatriNat', 'Validé', '1.01', true),
        (1602, 68, 'IS_GISEMENT_FOSSILIFERE', 'IS_GISEMENT_FOSSILIFERE', 'Gisement fossilifère', 'Gisement fossilifère', 'CICADA/PatriNat', 'Validé', '1.01.01', true),
        (1603, 68, 'IS_ICHNOSITE', 'IS_ICHNOSITE', 'Ichnosite (site à empreintes fossiles)', 'Ichnosite (site à empreintes fossiles)', 'CICADA/PatriNat', 'Validé', '1.01.02', true),
        (1604, 68, 'IS_AFFLEUREMENT', 'IS_AFFLEUREMENT', 'Affleurement remarquable', 'Affleurement remarquable', 'CICADA/PatriNat', 'Validé', '1.02', true),
        (1605, 68, 'IS_STRATOTYPE', 'IS_STRATOTYPE', 'Stratotype / coupe stratigraphique', 'Stratotype / coupe stratigraphique', 'CICADA/PatriNat', 'Validé', '1.03', true),
        (1606, 68, 'IS_TECTONIQUE', 'IS_TECTONIQUE', 'Site tectonique ou structural', 'Site tectonique ou structural', 'CICADA/PatriNat', 'Validé', '1.04', true),
        (1607, 68, 'IS_MINERALOGIQUE', 'IS_MINERALOGIQUE', 'Site minéralogique', 'Site minéralogique', 'CICADA/PatriNat', 'Validé', '1.05', true),
        (1608, 68, 'IS_VOLCANIQUE', 'IS_VOLCANIQUE', 'Site volcanique', 'Site volcanique', 'CICADA/PatriNat', 'Validé', '1.06', true),
        (1609, 68, 'IS_GEOMORPHO', 'IS_GEOMORPHO', 'Site géomorphologique, paysage géologique remarquable', 'Site géomorphologique, paysage géologique remarquable', 'CICADA/PatriNat', 'Validé', '1.07', true),
        (1610, 68, 'IS_HYDROGEO', 'IS_HYDROGEO', 'Site hydrogéologique', 'Site hydrogéologique', 'CICADA/PatriNat', 'Validé', '1.08', true),
        (1611, 68, 'IS_SOUTERRAIN', 'IS_SOUTERRAIN', 'Site souterrain', 'Site souterrain', 'CICADA/PatriNat', 'Validé', '1.09', true),
        (1612, 68, 'IS_CAVITE_NATURELLE', 'IS_CAVITE_NATURELLE', 'Cavité naturelle', 'Cavité naturelle', 'CICADA/PatriNat', 'Validé', '1.09.01', true),
        (1613, 68, 'IS_CAVITE_ANTHROPIQUE', 'IS_CAVITE_ANTHROPIQUE', 'Cavité anthropique', 'Cavité anthropique', 'CICADA/PatriNat', 'Validé', '1.09.02', true),
        (1614, 68, 'IS_HISTORIQUE', 'IS_HISTORIQUE', 'Site historique (localité type, site fondateur, lieu de découverte)', 'Site historique (localité type, site fondateur, lieu de découverte)', 'CICADA/PatriNat', 'Validé', '1.10', true),
        (1615, 68, 'IS_AUTRE', 'IS_AUTRE', 'Autre', 'Autre', 'CICADA/PatriNat', 'Validé', '1.11', true),
        (1616, 68, 'ES_COLL_PALEO', 'ES_COLL_PALEO', 'Collection paléontologique', 'Collection paléontologique', 'CICADA/PatriNat', 'Validé', '2.01', true),
        (1617, 68, 'ES_COLL_MINERALOGIQUE', 'ES_COLL_MINERALOGIQUE', 'Collection minéralogique', 'Collection minéralogique', 'CICADA/PatriNat', 'Validé', '2.02', true),
        (1618, 68, 'ES_COLL_LITHOLOGIQUE', 'ES_COLL_LITHOLOGIQUE', 'Collection lithologique', 'Collection lithologique', 'CICADA/PatriNat', 'Validé', '2.03', true),
        (1619, 68, 'ES_AUTRE', 'ES_AUTRE', 'Autre', 'Autre', 'CICADA/PatriNat', 'Validé', '2.04', true)
ON CONFLICT (id_nomenclature) DO UPDATE SET
    id_type = EXCLUDED.id_type, cd_nomenclature = EXCLUDED.cd_nomenclature, mnemonique = EXCLUDED.mnemonique,
    label = EXCLUDED.label, hierarchy = EXCLUDED.hierarchy, actif = EXCLUDED.actif;

UPDATE general.cor_enjeu_objet_geologique c SET id_objet_geologique = n.id_nomenclature
  FROM ref_nomenclatures.t_nomenclatures n WHERE n.id_type = 68 AND n.cd_nomenclature = c.code;

DELETE FROM general.cor_enjeu_objet_geologique WHERE id_objet_geologique IS NULL;"""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_initial'),
        ('plans', '0087_corenjeufichier'),
    ]

    operations = [
        # 1) lever l'ancienne unicité (id_enjeu, code) — SQL direct car la table
        #    est schema-qualifiée (alter_unique_together n'introspecte pas bien).
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.AlterUniqueTogether(name='corenjeuobjetgeologique', unique_together=set())],
            database_operations=[migrations.RunSQL('ALTER TABLE general.cor_enjeu_objet_geologique DROP CONSTRAINT IF EXISTS cor_enjeu_objet_geologique_id_enjeu_code_2a9576c0_uniq;', reverse_sql=migrations.RunSQL.noop)],
        ),
        # 2) FK nullable temporaire
        migrations.AddField(
            model_name='corenjeuobjetgeologique',
            name='id_objet_geologique',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, db_column='id_objet_geologique', related_name='enjeux_objet_geologique', limit_choices_to={'id_type__mnemonique': 'TYPE_OBJET_GEOLOGIQUE'}, to='core.nomenclature', verbose_name='Objet géologique'),
        ),
        # 3) seed nomenclatures + mapping (SQL brut auto-suffisant)
        migrations.RunSQL(SEED_AND_MAP_SQL, reverse_sql=migrations.RunSQL.noop),
        # 4) retirer code + libelle
        migrations.RemoveField(model_name='corenjeuobjetgeologique', name='code'),
        migrations.RemoveField(model_name='corenjeuobjetgeologique', name='libelle'),
        # 5) FK non-null
        migrations.AlterField(
            model_name='corenjeuobjetgeologique',
            name='id_objet_geologique',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, db_column='id_objet_geologique', related_name='enjeux_objet_geologique', limit_choices_to={'id_type__mnemonique': 'TYPE_OBJET_GEOLOGIQUE'}, to='core.nomenclature', verbose_name='Objet géologique', help_text="Type d'objet géologique (nomenclature TYPE_OBJET_GEOLOGIQUE)"),
        ),
        # 6) nouvelle unicité (id_enjeu, id_objet_geologique) — SQL direct
        migrations.SeparateDatabaseAndState(
            state_operations=[migrations.AlterUniqueTogether(name='corenjeuobjetgeologique', unique_together={('id_enjeu', 'id_objet_geologique')})],
            database_operations=[migrations.RunSQL('ALTER TABLE general.cor_enjeu_objet_geologique ADD CONSTRAINT cor_enjeu_obj_geo_enjeu_obj_uniq UNIQUE (id_enjeu, id_objet_geologique);', reverse_sql=migrations.RunSQL.noop)],
        ),
    ]
