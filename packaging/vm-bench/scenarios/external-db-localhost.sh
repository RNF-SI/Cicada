# DESCRIPTION: PostgreSQL sur le serveur CICADA lui-même, « localhost » saisi : refus immédiat et expliqué (cas non pris en charge)
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh.
#
# Vu de l'application (dans un conteneur), « localhost » désigne le conteneur.
# Le PostgreSQL installé directement sur le serveur CICADA n'est pas encore
# pris en charge par le formulaire : il doit le dire tout de suite, au lieu
# de démarrer l'application et de la laisser échouer des minutes plus tard
# (comportement d'avant, #223). Pour une base sur une autre machine, voir
# external-db-remote.

. "$BENCH_DIR/guest/prereq-postgres.sh"

EXPECT_REFUSAL="désigne ce serveur-ci"

scenario_prereqs() {
    install_host_postgres || return 1
    pg "CREATE ROLE ccd_operateur LOGIN CREATEDB PASSWORD 'Bench-Ext-Pass-1'"
}

scenario_db_answers() {
    cat <<'JSON'
"db_type": "existing",
  "db_host": "localhost",
  "db_port": "5432",
  "db_name": "cicada",
  "db_user": "ccd_operateur",
  "db_password": "Bench-Ext-Pass-1"
JSON
}
