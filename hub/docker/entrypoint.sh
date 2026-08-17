#!/bin/bash
# Démarrage du hub d'exploration.
#
# Beaucoup plus court que celui de CICADA : pas de superutilisateur à créer, pas
# de référentiel taxonomique à importer, pas de fichiers statiques à collecter.
# Deux référentiels seulement, et ils sont petits.
set -e

echo "=== Hub d'exploration — démarrage ==="

echo "→ Attente de PostgreSQL (${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432})…"
until nc -z "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}"; do
  sleep 1
done
echo "  PostgreSQL est prêt."

echo "→ Migrations…"
python manage.py migrate --noinput

# Les deux référentiels sont ignorés s'ils sont déjà chargés : le redémarrage
# d'un hub qui tourne depuis des mois ne doit pas coûter un réimport.
echo "→ Référentiel géographique…"
python manage.py import_ref_geo

echo "→ Nomenclatures…"
python manage.py import_nomenclatures

echo "=== Prêt ==="
exec "$@"
