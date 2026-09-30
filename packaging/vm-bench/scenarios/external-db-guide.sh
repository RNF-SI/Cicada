# DESCRIPTION: PostgreSQL hôte préparé en suivant le guide à la lettre (listen_addresses, pg_hba 172.17, cicada-prepare-db)
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh.
#
# Chemin documenté aujourd'hui (docs/INSTALLATION_GUIDE.md, étape 3) : sert de
# référence pour savoir si la procédure actuelle fonctionne telle qu'écrite.

. "$BENCH_DIR/guest/prereq-postgres.sh"

DB_PASSWORD="Bench-Guide-Pass-1"

scenario_prereqs() {
    install_host_postgres || return 1
    local conf hba
    conf="$(pg 'show config_file')"; hba="$(pg 'show hba_file')"
    # « listen_addresses = '*' » et « host all all 172.17.0.0/16 md5 » (guide)
    sed -i "s/^#\?listen_addresses.*/listen_addresses = '*'/" "$conf"
    echo "host    all    all    172.17.0.0/16    md5" >> "$hba"
    systemctl restart postgresql
    wait_for 30 sudo -u postgres psql -Atc 'select 1' || return 1

    # cicada-prepare-db est fourni par le paquet : on le lance après
    # l'installation du .deb, comme le guide (étape 3 après étape 2).
    :
}

# Appelé par run-scenario.sh juste avant le formulaire, via le hook ci-dessous.
before_form() {
    if out="$(cicada-prepare-db --password "$DB_PASSWORD" -y 2>&1)"; then
        record PASS "cicada-prepare-db (mode non interactif)"
    else
        record FAIL "cicada-prepare-db (mode non interactif)" "$(echo "$out" | tail -3)"
    fi
    echo "$out" | sed 's/\x1b\[[0-9;]*m//g' | sed -n '/Utilisez ces paramètres/,$p'
    DOCKER_HOST_IP="$(echo "$out" | sed 's/\x1b\[[0-9;]*m//g' | awk '/Hôte/{print $NF; exit}')"
    record INFO "Hôte conseillé par cicada-prepare-db" "${DOCKER_HOST_IP:-?}"
}

scenario_db_answers() {
    cat <<EOF
"db_type": "existing",
  "db_host": "${DOCKER_HOST_IP:-172.17.0.1}",
  "db_port": "5432",
  "db_name": "cicada",
  "db_user": "cicada_user",
  "db_password": "$DB_PASSWORD"
EOF
}

scenario_checks() {
    check "Aucun conteneur de base lancé (base externe)" \
        bash -c '! docker ps -a --format "{{.Names}}" | grep -qx cicada_prod_db'
}
