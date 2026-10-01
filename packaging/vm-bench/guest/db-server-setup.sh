#!/bin/bash
# Socle de la VM « serveur de base » : PostgreSQL 17 + PostGIS installés et
# ouverts au réseau, comme le serveur de bases mutualisé de RNF (conteneur ou
# VM dédiés aux bases, distincts de celui de l'application). Une autre
# application (« geonature ») y a déjà sa base : on vérifie ensuite que la
# préparation de CICADA ne la dérange pas.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
BENCH_DIR="${BENCH_DIR:-/home/ubuntu/bench}"
. "$BENCH_DIR/guest/lib.sh"
RESULTS=/dev/null
. "$BENCH_DIR/guest/prereq-postgres.sh"

apt-get update -qq
install_host_postgres
conf="$(pg 'show config_file')"; hba="$(pg 'show hba_file')"
sed -i "s/^#\?listen_addresses.*/listen_addresses = '*'/" "$conf"
pg "CREATE ROLE geonatadmin LOGIN PASSWORD 'gn-pass'"
pg "CREATE DATABASE geonature OWNER geonatadmin"
sudo -u postgres psql -d geonature -qc "CREATE EXTENSION postgis"
echo "host    geonature    geonatadmin    0.0.0.0/0    scram-sha-256" >> "$hba"
systemctl restart postgresql
echo "Serveur de base prêt : PostgreSQL $(pg 'show server_version'), listen_addresses=$(pg 'show listen_addresses')"
