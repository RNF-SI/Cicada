# DESCRIPTION: Serveur neuf, base PostGIS dans un conteneur (topologie du staging)
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh.

scenario_db_answers() {
    cat <<'EOF'
"db_type": "docker",
  "db_host": "db",
  "db_port": "5432",
  "db_name": "cicada",
  "db_user": "cicada_user",
  "db_password": "Bench-Db-Pass-1"
EOF
}

scenario_checks() {
    check "Conteneur base de données healthy" test "$(container_health cicada_prod_db)" = healthy
}
