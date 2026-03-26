-- Script d'initialisation PostgreSQL pour CICADA

-- Activation de l'extension PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Activation de l'extension UUID pour les clés uniques
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Création des schémas de l'application
-- Note : ces schémas sont aussi créés par les migrations Django (0001_create_schemas.py)
-- mais doivent pré-exister ici pour les GRANT et ALTER DEFAULT PRIVILEGES ci-dessous.
CREATE SCHEMA IF NOT EXISTS utilisateurs;
CREATE SCHEMA IF NOT EXISTS referentiels;
CREATE SCHEMA IF NOT EXISTS ref_nomenclatures;
CREATE SCHEMA IF NOT EXISTS ref_geo;
CREATE SCHEMA IF NOT EXISTS general;
CREATE SCHEMA IF NOT EXISTS fichiers;
CREATE SCHEMA IF NOT EXISTS ccd_commons;
CREATE SCHEMA IF NOT EXISTS ccd_notifications;
CREATE SCHEMA IF NOT EXISTS taxonomie;
CREATE SCHEMA IF NOT EXISTS ref_habitats;
CREATE SCHEMA IF NOT EXISTS ref_inpg;
CREATE SCHEMA IF NOT EXISTS ref_campanule;

-- Activation des extensions pour la recherche trigramme
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Configuration des permissions pour l'utilisateur de l'application
-- L'ordre des schémas suit le search_path Django (config/settings/base.py)
DO $$
DECLARE
    schema_name TEXT;
BEGIN
    FOR schema_name IN SELECT unnest(ARRAY[
        'utilisateurs', 'referentiels', 'ref_nomenclatures', 'ref_geo',
        'general', 'fichiers', 'ccd_commons', 'ccd_notifications',
        'taxonomie', 'ref_habitats', 'ref_inpg', 'ref_campanule'
    ])
    LOOP
        EXECUTE format('ALTER SCHEMA %I OWNER TO cicada_user', schema_name);
        EXECUTE format('GRANT USAGE, CREATE ON SCHEMA %I TO cicada_user', schema_name);
        EXECUTE format('GRANT ALL ON ALL TABLES IN SCHEMA %I TO cicada_user', schema_name);
        EXECUTE format('GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA %I TO cicada_user', schema_name);
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT ALL ON TABLES TO cicada_user', schema_name);
        EXECUTE format('ALTER DEFAULT PRIVILEGES IN SCHEMA %I GRANT USAGE, SELECT ON SEQUENCES TO cicada_user', schema_name);
    END LOOP;
END
$$;

-- Permissions sur le schéma public (pour les tables Django internes : auth, sessions, etc.)
GRANT USAGE, CREATE ON SCHEMA public TO cicada_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO cicada_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cicada_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cicada_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO cicada_user;

-- Message de confirmation
SELECT 'Base de données CICADA initialisée avec succès' AS status;