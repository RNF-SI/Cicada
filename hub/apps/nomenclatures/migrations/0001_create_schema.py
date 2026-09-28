"""Schéma ``ref_nomenclatures``."""

from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=[
                "CREATE SCHEMA IF NOT EXISTS ref_nomenclatures;",
                "COMMENT ON SCHEMA ref_nomenclatures IS "
                "'Nomenclatures de référence (compatible GeoNature)';",
            ],
            reverse_sql=["DROP SCHEMA IF EXISTS ref_nomenclatures CASCADE;"],
        ),
    ]
