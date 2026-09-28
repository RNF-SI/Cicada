"""
Schéma, extensions et configuration plein texte de l'index.

Ces objets doivent exister **avant** la table : ses deux colonnes générées
appellent `to_tsvector('public.french_unaccent', …)`, qui échouerait si la
configuration n'était pas déjà créée.
"""

from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql=[
                "CREATE SCHEMA IF NOT EXISTS ccd_search;",
                "COMMENT ON SCHEMA ccd_search IS "
                "'Index d''exploration agrégé du hub (#636)';",
                "CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public;",
                "CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA public;",
            ],
            reverse_sql=["DROP SCHEMA IF EXISTS ccd_search CASCADE;"],
        ),
        # Configuration plein texte française insensible aux accents : le
        # dictionnaire `french` radicalise (limicoles → limicol) mais ne retire
        # pas les accents, si bien que « foret » ne trouverait pas « forêt ».
        # On chaîne donc `unaccent` avant `french_stem`.
        #
        # Strictement identique à celle de CICADA : pendant la transition, les
        # deux index coexistent et doivent répondre pareil au même mot.
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_ts_config c
                    JOIN pg_namespace n ON n.oid = c.cfgnamespace
                    WHERE c.cfgname = 'french_unaccent' AND n.nspname = 'public'
                ) THEN
                    CREATE TEXT SEARCH CONFIGURATION public.french_unaccent
                        ( COPY = pg_catalog.french );
                    ALTER TEXT SEARCH CONFIGURATION public.french_unaccent
                        ALTER MAPPING FOR hword, hword_part, word
                        WITH unaccent, french_stem;
                END IF;
            END
            $$;
            """,
            reverse_sql=(
                "DROP TEXT SEARCH CONFIGURATION IF EXISTS public.french_unaccent;"
            ),
        ),
    ]
