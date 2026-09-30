# DESCRIPTION: PostgreSQL déjà présent sur le serveur, l'opérateur saisit « localhost » + un compte existant (#223, #269)
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh.
#
# Cible de #223 : l'opérateur a un PostgreSQL + PostGIS installé sur le
# serveur (cas GeoNature), avec un compte qui a le droit de créer une base.
# Il ne lance AUCUNE commande supplémentaire (ni cicada-prepare-db, ni
# réglage de listen_addresses / pg_hba.conf) : il saisit « localhost », ce
# compte et son mot de passe, et l'installateur fait le reste — créer la base,
# les extensions, les schémas.
#
# Le compte n'est PAS super-utilisateur : c'est le cas réaliste, et c'est ce
# qui rend la création de l'extension PostGIS délicate (#269).

. "$BENCH_DIR/guest/prereq-postgres.sh"

EXT_DB_USER="ccd_operateur"
EXT_DB_PASSWORD="Bench-Ext-Pass-1"

scenario_prereqs() {
    install_host_postgres || return 1
    pg "CREATE ROLE $EXT_DB_USER LOGIN CREATEDB PASSWORD '$EXT_DB_PASSWORD'"
    record INFO "PostgreSQL hôte" "$(pg 'show server_version'), listen_addresses=$(pg 'show listen_addresses'), compte $EXT_DB_USER (CREATEDB, non superuser)"
}

scenario_db_answers() {
    cat <<EOF
"db_type": "existing",
  "db_host": "localhost",
  "db_port": "5432",
  "db_name": "cicada",
  "db_user": "$EXT_DB_USER",
  "db_password": "$EXT_DB_PASSWORD"
EOF
}

scenario_checks() {
    check "Base « cicada » créée sur le PostgreSQL hôte" \
        test "$(pg "select 1 from pg_database where datname='cicada'")" = 1
    check "Extension PostGIS active dans la base (#269)" \
        test -n "$(sudo -u postgres psql -d cicada -Atc "select extversion from pg_extension where extname='postgis'" 2>/dev/null)"
    check "Aucun conteneur de base lancé (base externe)" \
        bash -c '! docker ps -a --format "{{.Names}}" | grep -qx cicada_prod_db'
}
