# Ajout de la catégorie FCR « Surveillance » (#370)
from django.db import migrations


def insert_categorie_fcr_surveillance(apps, schema_editor):
    """
    Insère la catégorie « Surveillance » dans CATEGORIE_FCR (id_type=44),
    en plus de Connaissance, Ancrage territorial, Fonctionnement et Autre.
    Idempotent via ON CONFLICT.
    """
    from django.db import connection
    with connection.cursor() as cur:
        # Le type CATEGORIE_FCR (id_type=44) est créé par l'import des
        # nomenclatures (import_nomenclatures), pas par les migrations. Sur une
        # base encore vierge de nomenclatures (ex. base de test), on ne fait
        # rien : l'import ajoutera « Surveillance » depuis nomenclatures_inserts.sql.
        cur.execute(
            "SELECT 1 FROM ref_nomenclatures.bib_nomenclatures_types WHERE id_type = 44;"
        )
        if not cur.fetchone():
            return
        cur.execute(
            """
            INSERT INTO ref_nomenclatures.t_nomenclatures
                (id_nomenclature, id_type, cd_nomenclature, mnemonique,
                 label, definition, source, statut, hierarchy,
                 date_ajout, date_maj, actif)
            VALUES (744, 44, 'SURVEILLANCE', 'SURVEILLANCE',
                    'Surveillance',
                    'FCR lié à la surveillance',
                    'CICADA', 'Validé', '5', NOW(), NOW(), true)
            ON CONFLICT (id_nomenclature) DO UPDATE SET
                cd_nomenclature = EXCLUDED.cd_nomenclature,
                mnemonique = EXCLUDED.mnemonique,
                label = EXCLUDED.label,
                definition = EXCLUDED.definition,
                hierarchy = EXCLUDED.hierarchy,
                actif = true;
            """
        )


def remove_categorie_fcr_surveillance(apps, schema_editor):
    """Reverse : retire la catégorie Surveillance."""
    from django.db import connection
    with connection.cursor() as cur:
        cur.execute(
            "DELETE FROM ref_nomenclatures.t_nomenclatures WHERE id_nomenclature = 744;"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0078_suiviinventaire_habitats_and_more"),
    ]

    operations = [
        migrations.RunPython(
            insert_categorie_fcr_surveillance,
            reverse_code=remove_categorie_fcr_surveillance,
        ),
    ]
