"""
Migration initiale pour créer les schémas PostgreSQL.
Cette migration doit être exécutée avant toutes les autres.
"""
from django.db import migrations


class Migration(migrations.Migration):
    """Crée les schémas PostgreSQL pour l'architecture multi-schéma."""

    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="""
            -- Création des schémas Cicada
            -- Compatible GeoNature et ODASE
            CREATE SCHEMA IF NOT EXISTS utilisateurs;
            CREATE SCHEMA IF NOT EXISTS referentiels;
            CREATE SCHEMA IF NOT EXISTS ref_nomenclatures;
            CREATE SCHEMA IF NOT EXISTS ref_geo;
            CREATE SCHEMA IF NOT EXISTS general;
            CREATE SCHEMA IF NOT EXISTS fichiers;
            CREATE SCHEMA IF NOT EXISTS ccd_commons;
            CREATE SCHEMA IF NOT EXISTS ccd_notifications;

            -- Attribution des permissions au user de l'application
            GRANT ALL ON SCHEMA utilisateurs TO CURRENT_USER;
            GRANT ALL ON SCHEMA referentiels TO CURRENT_USER;
            GRANT ALL ON SCHEMA ref_nomenclatures TO CURRENT_USER;
            GRANT ALL ON SCHEMA ref_geo TO CURRENT_USER;
            GRANT ALL ON SCHEMA general TO CURRENT_USER;
            GRANT ALL ON SCHEMA fichiers TO CURRENT_USER;
            GRANT ALL ON SCHEMA ccd_commons TO CURRENT_USER;
            GRANT ALL ON SCHEMA ccd_notifications TO CURRENT_USER;

            -- Commentaires sur les schémas
            COMMENT ON SCHEMA utilisateurs IS 'Schéma pour la gestion des utilisateurs et organismes (compatible GeoNature)';
            COMMENT ON SCHEMA referentiels IS 'Schéma pour les espaces protégés/sites (compatible ODASE)';
            COMMENT ON SCHEMA ref_nomenclatures IS 'Schéma pour les nomenclatures et référentiels (compatible GeoNature)';
            COMMENT ON SCHEMA ref_geo IS 'Schéma pour les référentiels géographiques (compatible GeoNature)';
            COMMENT ON SCHEMA general IS 'Schéma pour les plans de gestion (compatible ODASE)';
            COMMENT ON SCHEMA fichiers IS 'Schéma pour la gestion des fichiers (compatible ODASE)';
            COMMENT ON SCHEMA ccd_commons IS 'Schéma pour les utilitaires communs Cicada (modules, logs)';
            COMMENT ON SCHEMA ccd_notifications IS 'Schéma pour les notifications et validations Cicada';
            """,
            reverse_sql="""
            DROP SCHEMA IF EXISTS ccd_notifications CASCADE;
            DROP SCHEMA IF EXISTS ccd_commons CASCADE;
            DROP SCHEMA IF EXISTS fichiers CASCADE;
            DROP SCHEMA IF EXISTS general CASCADE;
            DROP SCHEMA IF EXISTS ref_geo CASCADE;
            DROP SCHEMA IF EXISTS ref_nomenclatures CASCADE;
            DROP SCHEMA IF EXISTS referentiels CASCADE;
            DROP SCHEMA IF EXISTS utilisateurs CASCADE;
            """
        ),
    ]
