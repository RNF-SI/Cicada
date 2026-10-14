# DESCRIPTION: Installation standard (base en conteneur) puis désinstallation : tout s'arrête, les données restent
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh.

. "$BENCH_DIR/scenarios/fresh-dockerdb.sh"

scenario_checks() {
    step "Désinstallation (apt remove)"
    if out="$(apt-get remove -y cicada 2>&1)"; then
        record PASS "apt remove cicada"
    else
        record FAIL "apt remove cicada" "$(echo "$out" | tail -3)"
    fi
    local restants
    restants="$(docker ps --format '{{.Names}}' | grep '^cicada_prod_' | tr '\n' ' ')"
    if [ -z "$restants" ]; then
        record PASS "Plus aucun conteneur CICADA lancé"
    else
        record FAIL "Plus aucun conteneur CICADA lancé" "encore lancés : $restants"
    fi
    check "Volume de la base conservé (remove ≠ purge)" docker volume inspect cicada_postgres_data
    check "Installateur web arrêté" bash -c '! systemctl is-active --quiet cicada-installer'
}
