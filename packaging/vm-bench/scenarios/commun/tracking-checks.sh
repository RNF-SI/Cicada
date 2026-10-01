# Contrôles « serveur de suivi + dépôt APT », partagés par tracking et a-z.
# shellcheck shell=bash
# Prérequis : VM tracking (bench.sh) et instance installée depuis le dépôt.

me_field() {  # me_field CHAMP — valeur connue de l'API de suivi pour cette instance
    curl -s --max-time 10 -H "X-Instance-Token: $(cat /etc/cicada/instance_token)" \
        http://tracking.cicada.bench/api/instances/me/ \
        | python3 -c "import json,sys;v=json.load(sys.stdin).get('$1');print('' if v is None else v)" 2>/dev/null
}
json_field() { python3 -c "import json;v=json.load(open('$1')).get('$2');print('' if v is None else v)" 2>/dev/null; }

api() {  # api MÉTHODE CHEMIN [CORPS] — en super-admin, via le frontend
    local access
    access="$(curl -s --max-time 20 -H 'Content-Type: application/json' \
        -d "{\"username\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
        "http://127.0.0.1:$FRONTEND_PORT/api/auth/login/" \
        | python3 -c 'import json,sys;print(json.load(sys.stdin).get("access",""))' 2>/dev/null)"
    curl -s --max-time 30 -X "$1" -H "Authorization: Bearer $access" -H 'Content-Type: application/json' \
        ${3:+-d "$3"} "http://127.0.0.1:$FRONTEND_PORT$2"
}

tracking_suivi_checks() {
    local from="$BENCH_TRACKING_FROM" to
    to="$(dpkg-deb -f "$BENCH_DIR/cicada.deb" Version)"

    step "Suivi de l'instance (API de suivi)"
    check "Version $from connue de l'API de suivi" test "$(me_field version)" = "$from"
    check "Heartbeat : timer programmé chaque nuit (03:00)" \
        bash -c "systemctl show cicada-heartbeat.timer -p TimersCalendar | grep -q '03:00:00'"
    check "Heartbeat : prochain déclenchement planifié" \
        bash -c "[ -n \"\$(systemctl show cicada-heartbeat.timer -p NextElapseUSecRealtime --value)\" ]"
    systemctl start cicada-heartbeat.service
    check "Heartbeat reçu par l'API de suivi (last_heartbeat)" test -n "$(me_field last_heartbeat)"
    check "Heartbeat : mise à jour $to annoncée à l'instance" \
        test "$(json_field /var/lib/cicada/updates/update_available.json latest_version)" = "$to"
}

tracking_maj_checks() {
    local from="$BENCH_TRACKING_FROM" to
    to="$(dpkg-deb -f "$BENCH_DIR/cicada.deb" Version)"

    step "Release : publication de $to dans le dépôt"
    touch "$BENCH_DIR/rdv-publier"
    wait_for 300 test -f "$BENCH_DIR/rdv-publier.ok" || { record FAIL "Publication de $to" "délai dépassé"; return; }
    apt-get update -qq 2>/dev/null
    check "apt voit cicada $to dans le dépôt" bash -c "apt-cache policy cicada | grep -q 'Candidat *: *$to\|Candidate: *$to'"

    step "Mise à jour depuis l'application (bouton « Mettre à jour »)"
    api GET /api/system/version/ > "$BENCH_DIR/system-version.json"
    if [ "$(json_field "$BENCH_DIR/system-version.json" update_available)" = True ]; then
        record PASS "L'application annonce la mise à jour $to"
    else
        record FAIL "L'application annonce la mise à jour $to" "$(head -c 200 "$BENCH_DIR/system-version.json")"
    fi
    api POST /api/system/trigger-update/ "{\"version\":\"$to\"}" > "$BENCH_DIR/trigger.json"
    record INFO "Réponse au clic « Mettre à jour »" "$(head -c 200 "$BENCH_DIR/trigger.json")"
    if wait_for 30 bash -c 'test -f /var/lib/cicada/updates/update_trigger.json || test -f /var/lib/cicada/updates/update_result.json'; then
        record PASS "Le clic parvient à l'updater de l'hôte"
    else
        record FAIL "Le clic parvient à l'updater de l'hôte" "aucun update_trigger.json sur l'hôte"
        # Pour tester quand même l'updater, poser le déclencheur comme le bouton le devrait
        note "contournement : déclencheur posé directement sur l'hôte"
        printf '{"version": "%s", "requested_by": "banc"}' "$to" > /var/lib/cicada/updates/update_trigger.json
    fi

    if wait_for 900 test -f /var/lib/cicada/updates/update_result.json; then
        if [ "$(json_field /var/lib/cicada/updates/update_result.json success)" = True ]; then
            record PASS "Updater : mise à jour terminée" "$(tail -1 /var/log/cicada/updater.log)"
        else
            record FAIL "Updater : mise à jour terminée" "$(json_field /var/lib/cicada/updates/update_result.json error)"
        fi
    else
        record FAIL "Updater : mise à jour terminée" "pas de résultat ; $(tail -2 /var/log/cicada/updater.log 2>/dev/null)"
    fi
    check "Paquet cicada $to installé" test "$(dpkg-query -W -f '${Version}' cicada)" = "$to"
    local c tag
    for c in cicada_prod_web cicada_prod_frontend cicada_prod_celery_worker cicada_prod_celery_beat; do
        tag="$(docker inspect -f '{{.Config.Image}}' "$c" 2>/dev/null)"
        if [ "${tag##*:}" = "$to" ]; then record PASS "$c sur l'image $to"
        else record FAIL "$c sur l'image $to" "image : ${tag:-absent}"; fi
    done
    wait_for 900 test "$(container_health cicada_prod_web)" = healthy
    wait_for 120 test "$(http_code "http://127.0.0.1:$FRONTEND_PORT/")" = 200
    check "Application servie après la mise à jour" test "$(http_code "http://127.0.0.1:$FRONTEND_PORT/")" = 200

    step "Heartbeat après la mise à jour"
    systemctl start cicada-heartbeat.service
    check "L'API de suivi connaît la version $to" test "$(me_field version)" = "$to"
    check "Plus de mise à jour annoncée" \
        test "$(json_field /var/lib/cicada/updates/update_available.json update_available)" = False
}
