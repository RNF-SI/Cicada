-- Script d'initialisation PostgreSQL pour CICADA

-- Activation de l'extension PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Activation de l'extension UUID pour les clés uniques
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Création des schémas de l'application
CREATE SCHEMA IF NOT EXISTS utilisateurs;
CREATE SCHEMA IF NOT EXISTS referentiels;
CREATE SCHEMA IF NOT EXISTS general;
CREATE SCHEMA IF NOT EXISTS taxonomie;
CREATE SCHEMA IF NOT EXISTS ref_habitats;

-- Activation des extensions pour la recherche trigramme
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Configuration des permissions pour l'utilisateur de l'application
GRANT USAGE ON SCHEMA utilisateurs TO cicada_user;
GRANT USAGE ON SCHEMA referentiels TO cicada_user;
GRANT USAGE ON SCHEMA general TO cicada_user;
GRANT USAGE ON SCHEMA taxonomie TO cicada_user;
GRANT USAGE ON SCHEMA ref_habitats TO cicada_user;

GRANT CREATE ON SCHEMA utilisateurs TO cicada_user;
GRANT CREATE ON SCHEMA referentiels TO cicada_user;
GRANT CREATE ON SCHEMA general TO cicada_user;
GRANT CREATE ON SCHEMA taxonomie TO cicada_user;
GRANT CREATE ON SCHEMA ref_habitats TO cicada_user;

-- Configuration des permissions pour les séquences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA utilisateurs TO cicada_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA referentiels TO cicada_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA general TO cicada_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA taxonomie TO cicada_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA ref_habitats TO cicada_user;

-- Configuration par défaut pour les futurs objets
ALTER DEFAULT PRIVILEGES IN SCHEMA utilisateurs GRANT ALL ON TABLES TO cicada_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA referentiels GRANT ALL ON TABLES TO cicada_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA general GRANT ALL ON TABLES TO cicada_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA taxonomie GRANT ALL ON TABLES TO cicada_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA ref_habitats GRANT ALL ON TABLES TO cicada_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA utilisateurs GRANT USAGE, SELECT ON SEQUENCES TO cicada_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA referentiels GRANT USAGE, SELECT ON SEQUENCES TO cicada_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA general GRANT USAGE, SELECT ON SEQUENCES TO cicada_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA taxonomie GRANT USAGE, SELECT ON SEQUENCES TO cicada_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA ref_habitats GRANT USAGE, SELECT ON SEQUENCES TO cicada_user;

-- Configuration des paramètres pour le français
SET lc_messages TO 'fr_FR.UTF-8';
SET lc_monetary TO 'fr_FR.UTF-8';
SET lc_numeric TO 'fr_FR.UTF-8';
SET lc_time TO 'fr_FR.UTF-8';

-- Message de confirmation
SELECT 'Base de données CICADA initialisée avec succès' AS status;