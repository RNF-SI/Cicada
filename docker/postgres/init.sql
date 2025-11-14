-- Script d'initialisation PostgreSQL pour Outil Plan de Gestion

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

-- Configuration des permissions pour l'utilisateur de l'application
GRANT USAGE ON SCHEMA utilisateurs TO outil_user;
GRANT USAGE ON SCHEMA referentiels TO outil_user;
GRANT USAGE ON SCHEMA general TO outil_user;

GRANT CREATE ON SCHEMA utilisateurs TO outil_user;
GRANT CREATE ON SCHEMA referentiels TO outil_user;
GRANT CREATE ON SCHEMA general TO outil_user;

-- Configuration des permissions pour les séquences
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA utilisateurs TO outil_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA referentiels TO outil_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA general TO outil_user;

-- Configuration par défaut pour les futurs objets
ALTER DEFAULT PRIVILEGES IN SCHEMA utilisateurs GRANT ALL ON TABLES TO outil_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA referentiels GRANT ALL ON TABLES TO outil_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA general GRANT ALL ON TABLES TO outil_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA utilisateurs GRANT USAGE, SELECT ON SEQUENCES TO outil_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA referentiels GRANT USAGE, SELECT ON SEQUENCES TO outil_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA general GRANT USAGE, SELECT ON SEQUENCES TO outil_user;

-- Configuration des paramètres pour le français
SET lc_messages TO 'fr_FR.UTF-8';
SET lc_monetary TO 'fr_FR.UTF-8';
SET lc_numeric TO 'fr_FR.UTF-8';
SET lc_time TO 'fr_FR.UTF-8';

-- Message de confirmation
SELECT 'Base de données Outil Plan de Gestion initialisée avec succès' AS status;