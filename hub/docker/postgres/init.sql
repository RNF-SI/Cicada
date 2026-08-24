-- Initialisation PostgreSQL du hub d'exploration.
--
-- Nettement plus court que celui de CICADA : le hub n'a ni utilisateurs, ni
-- sites, ni plans, ni référentiels taxonomiques. Trois schémas suffisent.
--
-- Les schémas sont AUSSI créés par les migrations Django (0001_create_schema de
-- chaque app), pour que le projet reste installable sur une base existante qui
-- n'aurait pas été initialisée par ce script.

CREATE EXTENSION IF NOT EXISTS postgis;

-- Recherche plein texte tolérante aux fautes de frappe et aux accents.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE SCHEMA IF NOT EXISTS ccd_search;
CREATE SCHEMA IF NOT EXISTS ref_geo;
CREATE SCHEMA IF NOT EXISTS ref_nomenclatures;
