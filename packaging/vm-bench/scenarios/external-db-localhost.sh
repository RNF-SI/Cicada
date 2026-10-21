# DESCRIPTION: PostgreSQL installé sur le serveur CICADA lui-même (hors Docker), « localhost » saisi : préparation --docker-local, installation, connexion des conteneurs
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh.
#
# Vu d'un conteneur, « localhost » désigne le conteneur. L'installateur écrit
# donc POSTGRES_HOST=host.docker.internal, que docker-compose.yml relie au
# serveur (host-gateway), et cicada-prepare-db --docker-local autorise les
# réseaux Docker. Le test du formulaire passe par le pont Docker ; seule une
# installation réelle prouve que les conteneurs joignent la base. Une autre
# application (« geonature ») a déjà sa base sur ce PostgreSQL.
#
# Parcours de l'opérateur : PostgreSQL installé tel que le livre Debian
# (listen_addresses = 'localhost'), le script l'explique, l'opérateur passe à
# '*', relance, reporte le mot de passe affiché, teste, installe.

. "$BENCH_DIR/guest/prereq-postgres.sh"

DB_NAME="cicada"
DB_USER="cicada_user"
DB_PASSWORD="pas-encore-connu"

scenario_prereqs() {
    install_host_postgres || return 1
    pg "CREATE ROLE geonatadmin LOGIN PASSWORD 'gn-pass'"
    pg "CREATE DATABASE geonature OWNER geonatadmin"
}

api_test_db() {  # api_test_db HOTE MOTDEPASSE → JSON des contrôles
    curl -s --max-time 30 -H 'Content-Type: application/json' \
        -d "{\"db_host\":\"$1\",\"db_port\":\"5432\",\"db_name\":\"$DB_NAME\",\"db_user\":\"$DB_USER\",\"db_password\":\"$2\"}" \
        http://127.0.0.1:4567/api/test-db
}
statuses() { python3 -c "import json,sys;print(' '.join(c['status'] for c in json.load(sys.stdin)['checks']))"; }
labels()   { python3 -c "import json,sys;print(' | '.join(c['label'] for c in json.load(sys.stdin)['checks']))"; }
strip()    { sed 's/\x1b\[[0-9;]*m//g'; }

before_form() {
    local out result
    check "Le formulaire propose la préparation locale pour « localhost »" bash -c \
        "curl -s 'http://127.0.0.1:4567/api/db-client-ip?host=localhost' | python3 -c 'import json,sys;assert json.load(sys.stdin)[\"local\"] is True'"

    check "Une liste d'adresses est refusée (une seule attendue)" bash -c \
        "curl -s -H 'Content-Type: application/json' -d '{\"db_host\":\"127.0.0.1, 10.0.0.1\",\"db_name\":\"x\",\"db_user\":\"x\"}' \
         http://127.0.0.1:4567/api/test-db | python3 -c 'import json,sys;print(json.load(sys.stdin))' | grep -q 'une seule adresse'"

    step "Préparation de la base (PostgreSQL livré en listen_addresses = 'localhost')"
    out="$(cicada-prepare-db --docker-local 2>&1 | strip)"
    check "Le script refuse et explique listen_addresses" bash -c "echo \"\$1\" | grep -q \"listen_addresses = '\\*'\"" _ "$out"

    sudo -u postgres psql -Atc "ALTER SYSTEM SET listen_addresses = '*'" >/dev/null
    systemctl restart postgresql
    wait_for 30 sudo -u postgres psql -Atc 'select 1'

    if out="$(cicada-prepare-db --docker-local 2>&1 | strip)"; then
        record PASS "cicada-prepare-db --docker-local"
    else
        record FAIL "cicada-prepare-db --docker-local" "$(echo "$out" | grep -v '^\s*$' | tail -2)"
    fi
    echo "$out"
    check "Le script indique « localhost » comme hôte" bash -c "echo \"\$1\" | grep -qE 'Hôte +: localhost'" _ "$out"
    DB_PASSWORD="$(echo "$out" | awk -F': *' '/Mot de passe  *:/{split($2,a," "); print a[1]; exit}')"
    check "Mot de passe affiché par le script" test -n "$DB_PASSWORD"

    result="$(api_test_db localhost "$DB_PASSWORD")"
    if [ "$(echo "$result" | statuses)" = "ok ok ok" ]; then
        record PASS "Test de connexion du formulaire avec « localhost »" "$(echo "$result" | labels)"
    else
        record FAIL "Test de connexion du formulaire avec « localhost »" "$(echo "$result" | labels)"
    fi
}

scenario_db_answers() {
    cat <<EOF
"db_type": "existing",
  "db_host": "localhost",
  "db_port": "5432",
  "db_name": "$DB_NAME",
  "db_user": "$DB_USER",
  "db_password": "$DB_PASSWORD"
EOF
}

scenario_checks() {
    check "Aucun conteneur de base lancé (PostgreSQL de l'hôte)" \
        bash -c '! docker ps -a --format "{{.Names}}" | grep -qx cicada_prod_db'
    check "POSTGRES_HOST=host.docker.internal dans le .env" \
        grep -qx 'POSTGRES_HOST=host.docker.internal' /var/lib/cicada/.env
    check "Le conteneur web lit et écrit dans la base de l'hôte" \
        test "$(app_sql "select count(*) from utilisateurs.t_roles where email='$ADMIN_EMAIL'")" = 1
    check "Les données sont bien dans le PostgreSQL de l'hôte" \
        test "$(sudo -u postgres psql -d "$DB_NAME" -Atc "select count(*) from utilisateurs.t_roles where email='$ADMIN_EMAIL'")" = 1
    check "Le worker Celery joint aussi la base" bash -c \
        "docker exec cicada_prod_celery_worker python -c \"
import os, psycopg
psycopg.connect(host=os.environ['POSTGRES_HOST'], dbname=os.environ['POSTGRES_DB'], user=os.environ['POSTGRES_USER'],
                password=os.environ['POSTGRES_PASSWORD'], connect_timeout=5).close()\""
    check "L'autre application (geonature) garde sa base" \
        test "$(pg "select count(*) from pg_database where datname='geonature'")" = 1
}
