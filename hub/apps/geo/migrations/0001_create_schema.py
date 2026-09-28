"""Schéma ``ref_geo`` et extension PostGIS."""

from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=[
                "CREATE EXTENSION IF NOT EXISTS postgis;",
                "CREATE SCHEMA IF NOT EXISTS ref_geo;",
                "COMMENT ON SCHEMA ref_geo IS "
                "'Référentiel géographique administratif (compatible GeoNature)';",
            ],
            reverse_sql=["DROP SCHEMA IF EXISTS ref_geo CASCADE;"],
        ),
    ]
