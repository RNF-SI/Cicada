# #452 — Format de présentation d'une métrique (simple / grille)
#
# Ajoute le champ FK `Metrique.format_metrique` et seede la nomenclature
# FORMAT_METRIQUE (type 69) avec ses items SIMPLE (1370) et GRILLE (1371).
# Le seed est idempotent (ON CONFLICT) et ne s'exécute que si les nomenclatures
# ont déjà été importées (sinon import_nomenclatures les ajoutera depuis les
# fichiers SQL sur une base vierge).
import django.db.models.deletion
from django.db import migrations, models


def insert_format_metrique(apps, schema_editor):
    from django.db import connection
    with connection.cursor() as cur:
        # Garde : sur une base encore vierge de nomenclatures (ex. base de test),
        # le type TYPE_METRIQUE (48) n'existe pas encore → ne rien faire, l'import
        # ajoutera FORMAT_METRIQUE depuis types_inserts.sql / nomenclatures_inserts.sql.
        cur.execute(
            "SELECT 1 FROM ref_nomenclatures.bib_nomenclatures_types WHERE id_type = 48;"
        )
        if not cur.fetchone():
            return

        # Type FORMAT_METRIQUE (69)
        cur.execute(
            """
            INSERT INTO ref_nomenclatures.bib_nomenclatures_types
                (id_type, mnemonique, label, definition, source, statut, date_ajout, date_maj)
            VALUES (69, 'FORMAT_METRIQUE', 'Format de métrique',
                    'Format de présentation de la métrique (simple, grille)',
                    'CICADA', 'Validé', NOW(), NOW())
            ON CONFLICT (id_type) DO UPDATE SET
                mnemonique = EXCLUDED.mnemonique,
                label = EXCLUDED.label,
                definition = EXCLUDED.definition;
            """
        )

        # Items SIMPLE (1370) / GRILLE (1371)
        cur.execute(
            """
            INSERT INTO ref_nomenclatures.t_nomenclatures
                (id_nomenclature, id_type, cd_nomenclature, mnemonique,
                 label, definition, source, statut, hierarchy,
                 date_ajout, date_maj, actif)
            VALUES
                (1370, 69, 'SIMPLE', 'SIMPLE', 'Simple',
                 'Saisie d''une valeur libre (sans grille de scoring)',
                 'CICADA', 'Validé', '1', NOW(), NOW(), true),
                (1371, 69, 'GRILLE', 'GRILLE', 'Grille',
                 'Grille de 5 niveaux (très mauvais à très bon) avec scoring automatique',
                 'CICADA', 'Validé', '2', NOW(), NOW(), true)
            ON CONFLICT (id_nomenclature) DO UPDATE SET
                id_type = EXCLUDED.id_type,
                cd_nomenclature = EXCLUDED.cd_nomenclature,
                mnemonique = EXCLUDED.mnemonique,
                label = EXCLUDED.label,
                definition = EXCLUDED.definition,
                hierarchy = EXCLUDED.hierarchy,
                actif = true;
            """
        )


def remove_format_metrique(apps, schema_editor):
    from django.db import connection
    with connection.cursor() as cur:
        cur.execute(
            "DELETE FROM ref_nomenclatures.t_nomenclatures WHERE id_nomenclature IN (1370, 1371);"
        )
        cur.execute(
            "DELETE FROM ref_nomenclatures.bib_nomenclatures_types WHERE id_type = 69;"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0089_alter_enjeu_rang"),
        ("core", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="metrique",
            name="format_metrique",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="metriques_format",
                db_column="format_metrique",
                to="core.nomenclature",
                limit_choices_to={"id_type__mnemonique": "FORMAT_METRIQUE"},
                help_text="Simple ou Grille",
                verbose_name="Format de métrique",
            ),
        ),
        migrations.RunPython(insert_format_metrique, reverse_code=remove_format_metrique),
    ]
