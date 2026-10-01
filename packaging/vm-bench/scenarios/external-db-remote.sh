# DESCRIPTION: PostgreSQL sur un autre serveur/conteneur (topologie RNF) : l'admin de la base lance la commande donnée par le formulaire
# DB_VM: oui
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh (VM CICADA) et guest/db-side.sh (VM base).
#
# Topologie RNF : les bases vivent dans un conteneur/VM dédiés, distincts de
# celui de CICADA. Parcours de l'opérateur, tel que le formulaire le décrit :
#   1. il choisit « Serveur PostgreSQL existant » et saisit l'adresse du serveur ;
#   2. sur le serveur de base, en root, il lance la commande affichée
#      (script récupéré auprès de l'installateur, init.sql inclus) ;
#   3. il reporte le mot de passe affiché, teste la connexion, installe.
# Une autre application (« geonature ») a déjà sa base sur ce serveur.

DB_NAME="cicada"
DB_USER="cicada_user"
DB_PASSWORD="pas-encore-connu"

# --- Côté serveur de base (exécuté par guest/db-side.sh) ---------------------
db_server_prepare() {
    local cicada_ip="$1" out
    # La commande affichée par le formulaire (étape 2)
    local cmd="curl -fsSL http://$cicada_ip:4567/prepare-db.sh | sudo bash -s -- --client $cicada_ip"
    note "$cmd"
    if out="$(bash -c "$cmd" 2>&1)"; then
        record PASS "Serveur de base : commande de préparation du formulaire"
    else
        record FAIL "Serveur de base : commande de préparation du formulaire" \
            "$(echo "$out" | sed 's/\x1b\[[0-9;]*m//g' | grep -v '^\s*$' | tail -2)"
    fi
    echo "$out" | sed 's/\x1b\[[0-9;]*m//g'
    # Le mot de passe affiché, que l'opérateur reporte dans le formulaire
    echo "$out" | sed 's/\x1b\[[0-9;]*m//g' | awk -F': *' '/Mot de passe  *:/{split($2,a," "); print a[1]; exit}' \
        > "$BENCH_DIR/base-prete"
    check "Serveur de base : la base geonature n'a pas été touchée" \
        test "$(pg "select count(*) from pg_database where datname='geonature'")" = 1
}

# --- Côté CICADA --------------------------------------------------------------
api_test_db() {  # api_test_db MOTDEPASSE → JSON des contrôles
    curl -s --max-time 30 -H 'Content-Type: application/json' \
        -d "{\"db_host\":\"$BENCH_DB_HOST\",\"db_port\":\"5432\",\"db_name\":\"$DB_NAME\",\"db_user\":\"$DB_USER\",\"db_password\":\"$1\"}" \
        http://127.0.0.1:4567/api/test-db
}
statuses() { python3 -c "import json,sys;print(' '.join(c['status'] for c in json.load(sys.stdin)['checks']))"; }
labels()   { python3 -c "import json,sys;print(' | '.join(c['label'] for c in json.load(sys.stdin)['checks']))"; }

before_form() {
    local my_ip client_ip result
    my_ip="$(hostname -I | awk '{print $1}')"
    client_ip="$(curl -s "http://127.0.0.1:4567/api/db-client-ip?host=$BENCH_DB_HOST" \
        | python3 -c 'import json,sys;print(json.load(sys.stdin)["client_ip"])')"
    check "Le formulaire propose --client $client_ip (adresse de ce serveur vue de la base)" test "$client_ip" = "$my_ip"

    # Les réponses JSON encodent les accents (\u00e9) : décoder avant de chercher
    check "« localhost » refusé avec explication" bash -c \
        "curl -s -H 'Content-Type: application/json' -d '{\"db_host\":\"localhost\",\"db_name\":\"x\",\"db_user\":\"x\"}' \
         http://127.0.0.1:4567/api/test-db | python3 -c 'import json,sys;print(json.load(sys.stdin))' | grep -q 'désigne ce serveur-ci'"

    result="$(api_test_db "$DB_PASSWORD")"
    record INFO "Test de connexion AVANT préparation" "$(echo "$result" | labels)"
    check "Test de connexion : base non préparée signalée" bash -c "echo '$(echo "$result" | statuses)' | grep -q error"

    # Le formulaire doit refuser tout de suite, sans rien démarrer
    answers_json > "$BENCH_DIR/answers-early.json"
    curl -s --max-time 60 -H 'Content-Type: application/json' --data @"$BENCH_DIR/answers-early.json" \
        http://127.0.0.1:4567/api/install > "$BENCH_DIR/install-early.json"
    check "Installation refusée avant préparation de la base, avec message" bash -c \
        "python3 -c 'import json;print(json.load(open(\"$BENCH_DIR/install-early.json\")))' | grep -q 'pas prête'"
    check "Rien n'a été démarré (pas de .env, pas de conteneur web)" \
        bash -c '[ ! -f /var/lib/cicada/.env ] && ! docker ps -a --format "{{.Names}}" | grep -qx cicada_prod_web'

    step "Préparation du serveur de base (par son administrateur)"
    touch "$BENCH_DIR/attente-base"
    wait_for 900 test -f "$BENCH_DIR/base-prete" || { record FAIL "Serveur de base préparé" "délai dépassé"; return; }
    DB_PASSWORD="$(cat "$BENCH_DIR/base-prete")"
    check "Mot de passe affiché par le script" test -n "$DB_PASSWORD"

    result="$(api_test_db "$DB_PASSWORD")"
    if [ "$(echo "$result" | statuses)" = "ok ok ok" ]; then
        record PASS "Test de connexion après préparation" "$(echo "$result" | labels)"
    else
        record FAIL "Test de connexion après préparation" "$(echo "$result" | labels)"
    fi
}

scenario_db_answers() {
    cat <<EOF
"db_type": "existing",
  "db_host": "$BENCH_DB_HOST",
  "db_port": "5432",
  "db_name": "$DB_NAME",
  "db_user": "$DB_USER",
  "db_password": "$DB_PASSWORD"
EOF
}

remote_sql() {  # remote_sql BASE UTILISATEUR MOTDEPASSE SQL — via le conteneur web
    docker exec cicada_prod_web python -c "
import psycopg
with psycopg.connect(host='$BENCH_DB_HOST', dbname='$1', user='$2', password='$3', connect_timeout=5) as c:
    print(c.execute('''$4''').fetchone()[0])" 2>&1 | tail -1
}

scenario_checks() {
    check "Aucun conteneur de base lancé (base externe)" \
        bash -c '! docker ps -a --format "{{.Names}}" | grep -qx cicada_prod_db'
    check "PostGIS actif dans la base CICADA distante" \
        test -n "$(app_sql "select extversion from pg_extension where extname='postgis'")"
    check "Index TaxRef sans accents créé (unaccent confiée au compte)" \
        test "$(app_sql "select count(*) from pg_indexes where indexname='idx_vm_taxref_autocomplete_unaccent'")" = 1
    check "L'autre application (geonature) accède toujours à sa base" \
        test "$(remote_sql geonature geonatadmin gn-pass 'select 1')" = 1
}
