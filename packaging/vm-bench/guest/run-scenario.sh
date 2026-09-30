#!/bin/bash
# Déroule un scénario DANS la VM (en root) : prérequis → paquet → formulaire
# d'installation → contrôles. Chaque contrôle est consigné dans results.tsv ;
# un contrôle en échec n'arrête pas le déroulé (on veut la liste complète des
# problèmes), seules les étapes sans lesquelles la suite n'a pas de sens
# arrêtent le scénario.
set -uo pipefail
export DEBIAN_FRONTEND=noninteractive

SCENARIO="$1"
. "$(dirname "$0")/lib.sh"
: > "$RESULTS"

# Valeurs communes à tous les scénarios (un scénario peut les surcharger)
ADMIN_EMAIL="admin@bench.test"
ADMIN_PASSWORD="Bench-Test-123!"
DOMAIN="cicada.bench.test"
FRONTEND_PORT=8080
# URL à laquelle l'opérateur doit être renvoyé en fin d'installation
EXPECTED_URL="http://$DOMAIN:$FRONTEND_PORT"

scenario_prereqs() { :; }
before_form()      { :; }
scenario_checks()  { :; }
# shellcheck source=/dev/null
. "$BENCH_DIR/scenarios/$SCENARIO.sh"

# Données du formulaire communes ; le scénario fournit la partie base de données
# via scenario_db_answers (fragment JSON sans accolades).
answers_json() {
    cat <<EOF
{
  "admin_email": "$ADMIN_EMAIL",
  "admin_password": "$ADMIN_PASSWORD",
  "admin_password_confirm": "$ADMIN_PASSWORD",
  "admin_nom": "Banc",
  "admin_prenom": "Test",
  "domain": "$DOMAIN",
  "frontend_port": "$FRONTEND_PORT",
  "backend_port": "8000",
  "use_traefik": false,
  "redis_host": "redis",
  "redis_port": "6379",
  "redis_password": "",
  "smtp_enabled": false,
  "smtp_use_auth": false,
  "smtp_use_tls": false,
  "federation_enabled": false,
  "federation_relay": false,
  "rgpd_consent": false,
  $(scenario_db_answers)
}
EOF
}

# ---------------------------------------------------------------------------
step "Préparation de la VM"
. /etc/os-release
note "$PRETTY_NAME — noyau $(uname -r)"

# Fausse API de suivi + blocage de la vraie : un banc ne doit jamais
# enregistrer d'instance dans l'API de production.
echo "127.0.0.1 tracking.cicada.reserves-naturelles.org" >> /etc/hosts
: > "$FAKE_TRACKING_LOG"
systemd-run --quiet --unit=bench-fake-tracking python3 "$BENCH_DIR/guest/fake-tracking.py" "$FAKE_TRACKING_LOG" 8099
wait_for 10 curl -sf "$FAKE_TRACKING_URL/instances/version/" || note "fausse API de suivi injoignable"

if [ "${BENCH_DEGRADED:-true}" = true ]; then
    # Un serveur de production porte presque toujours au moins une unité en
    # échec ; systemd se déclare alors « degraded » et non « running ».
    cat > /etc/systemd/system/bench-unite-en-echec.service <<'EOF'
[Unit]
Description=Banc CICADA - unite volontairement en echec (serveur degraded)
[Service]
Type=oneshot
ExecStart=/bin/false
EOF
    systemctl daemon-reload
    systemctl start bench-unite-en-echec.service 2>/dev/null || true
fi
record INFO "État systemd avant installation" "$(systemctl is-system-running 2>/dev/null)"

step "Prérequis du scénario"
scenario_prereqs || { record FAIL "Prérequis du scénario" "voir le journal"; exit 1; }

# ---------------------------------------------------------------------------
step "Installation du paquet"
PKG_VERSION="$(dpkg-deb -f "$BENCH_DIR/cicada.deb" Version)"
note "cicada $PKG_VERSION"
if apt_out="$(apt-get install -y "$BENCH_DIR/cicada.deb" 2>&1)"; then
    record PASS "apt install du .deb (dépendances résolues)"
else
    echo "$apt_out" | tail -20
    record FAIL "apt install du .deb (dépendances résolues)" "$(echo "$apt_out" | grep -E '^E:|Dépend|Depends' | head -3)"
    exit 1
fi
echo "$apt_out" | sed -n '/=====/,/=====/p'

# Rediriger l'installateur et le heartbeat vers la fausse API de suivi
sed -i "s|^TRACKING_API_URL=.*|TRACKING_API_URL=$FAKE_TRACKING_URL|" /etc/cicada/cicada.conf

# #222 — l'installateur doit tourner sans intervention après l'installation
if wait_for 30 curl -sf http://127.0.0.1:4567/api/health; then
    record PASS "Installateur web démarré automatiquement (#222)"
else
    record FAIL "Installateur web démarré automatiquement (#222)" \
        "cicada-installer : $(systemctl is-active cicada-installer 2>&1) / $(systemctl is-enabled cicada-installer 2>&1)"
    note "contournement : systemctl start cicada-installer"
    systemctl start cicada-installer
    wait_for 30 curl -sf http://127.0.0.1:4567/api/health \
        || { record FAIL "Installateur web démarrable" "$(journalctl -u cicada-installer --no-pager | tail -5)"; exit 1; }
fi
check "Installateur joignable depuis le réseau (0.0.0.0:4567)" \
    curl -sf "http://$(hostname -I | awk '{print $1}'):4567/api/health"

for timer in cicada-heartbeat.timer cicada-updater.path; do
    check "$timer actif" systemctl is-active --quiet "$timer"
done

# Heartbeat (#226) : le service tourne avec le Python système
systemctl start cicada-heartbeat.service >/dev/null 2>&1
hb_rc=$?
hb_log="$(journalctl -u cicada-heartbeat.service --no-pager 2>&1 | tail -20)"
if echo "$hb_log" | grep -q "ModuleNotFoundError"; then
    record FAIL "Heartbeat exécutable (#226)" "$(echo "$hb_log" | grep ModuleNotFoundError | head -1)"
elif [ "$hb_rc" -ne 0 ]; then
    record FAIL "Heartbeat exécutable (#226)" "$(echo "$hb_log" | tail -2)"
else
    record PASS "Heartbeat exécutable (#226)"
fi
# Les images cloud embarquent python3-requests (cloud-init en dépend), ce qui
# masque son absence ; une Debian minimale ne l'a pas. On vérifie donc que le
# paquet le déclare, puisque heartbeat et updater tournent avec le Python système.
if dpkg-deb -f "$BENCH_DIR/cicada.deb" Depends | grep -q 'python3-requests'; then
    record PASS "Dépendance python3-requests déclarée (heartbeat, #226)"
else
    record FAIL "Dépendance python3-requests déclarée (heartbeat, #226)" \
        "Depends: $(dpkg-deb -f "$BENCH_DIR/cicada.deb" Depends)"
fi
check "Heartbeat reçu par l'API de suivi" grep -q '/instances/heartbeat/' "$FAKE_TRACKING_LOG"

# ---------------------------------------------------------------------------
step "Formulaire d'installation (POST /api/install)"
before_form
answers_json > "$BENCH_DIR/answers.json"

# Suivi en direct de ce que voit l'opérateur dans le navigateur
(
    last=""
    while sleep 5; do
        msg="$(python3 -c 'import json;d=json.load(open("/var/lib/cicada/install_status.json"));print(d.get("message","")[:160])' 2>/dev/null)"
        web="$(container_health cicada_prod_web)"
        cur="$msg | web=${web:-absent}"
        if [ "$cur" != "$last" ]; then echo "   [$(date +%H:%M:%S)] $cur"; last="$cur"; fi
    done
) &
POLLER=$!

t0=$(date +%s)
curl -s --max-time 2400 -X POST -H 'Content-Type: application/json' \
    --data @"$BENCH_DIR/answers.json" http://127.0.0.1:4567/api/install \
    > "$BENCH_DIR/install-response.json"
curl_rc=$?
duration=$(( $(date +%s) - t0 ))
kill "$POLLER" 2>/dev/null
record INFO "Durée de l'installation (formulaire)" "${duration}s"

resp_get() { python3 -c "import json,sys;d=json.load(open('$BENCH_DIR/install-response.json'));v=d.get('$1');print('' if v is None else v if not isinstance(v,list) else '; '.join(v))" 2>/dev/null; }
# Dernière ligne significative d'une erreur (souvent une trace Python entière)
last_line() { grep -v '^[[:space:]]*$' | grep -v '^[[:space:]]*\^' | tail -1 | cut -c1-300; }

if [ "$curl_rc" -eq 0 ] && [ "$(resp_get success)" = "True" ]; then
    record PASS "Installation déclarée réussie par le formulaire"
else
    record FAIL "Installation déclarée réussie par le formulaire" \
        "$( { resp_get error; resp_get errors; } | last_line)"
    echo "---- Réponse complète de l'installateur ----"
    resp_get error
    resp_get errors
fi

redirect="$(resp_get redirect_url)"
if [ "$redirect" = "$EXPECTED_URL" ]; then
    record PASS "Redirection finale vers l'URL publique" "$redirect"
else
    record FAIL "Redirection finale vers l'URL publique (#223)" "obtenu « ${redirect:-rien} », attendu « $EXPECTED_URL »"
fi

# ---------------------------------------------------------------------------
step "Contrôles de l'instance"
check "Conteneur web healthy" test "$(container_health cicada_prod_web)" = healthy
for c in cicada_prod_frontend cicada_prod_celery_worker cicada_prod_celery_beat cicada_prod_redis; do
    state="$(container_health "$c")"
    case "$state" in running|healthy) record PASS "Conteneur $c démarré" ;;
                     *) record FAIL "Conteneur $c démarré" "état : ${state:-absent}" ;; esac
done

check "Frontend servi sur :$FRONTEND_PORT" test "$(http_code "http://127.0.0.1:$FRONTEND_PORT/")" = 200
if curl -s -D - -o /dev/null --max-time 10 "http://127.0.0.1:$FRONTEND_PORT/api/health/" | grep -qi '^x-correlation-id'; then
    record PASS "API CICADA joignable via le frontend (/api/health/)"
else
    record FAIL "API CICADA joignable via le frontend (/api/health/)" "code $(http_code "http://127.0.0.1:$FRONTEND_PORT/api/health/")"
fi

login_code="$(curl -s -o "$BENCH_DIR/login.json" -w '%{http_code}' --max-time 20 \
    -H 'Content-Type: application/json' -H "Host: $DOMAIN" \
    -d "{\"username\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
    "http://127.0.0.1:$FRONTEND_PORT/api/auth/login/")"
if [ "$login_code" = 200 ] && grep -q '"access"' "$BENCH_DIR/login.json"; then
    record PASS "Connexion du super-admin créé par le formulaire"
else
    record FAIL "Connexion du super-admin créé par le formulaire" "HTTP $login_code $(head -c 200 "$BENCH_DIR/login.json" 2>/dev/null)"
fi

if [ "$(container_health cicada_prod_web)" = healthy ]; then
    for spec in \
        "Nomenclatures importées|select count(*) from ref_nomenclatures.t_nomenclatures" \
        "HabRef importé|select count(*) from ref_habitats.habref" \
        "TaxRef importé|select count(*) from taxonomie.taxref" \
        "Découpage administratif importé|select count(*) from ref_geo.l_areas"; do
        label="${spec%%|*}"; sql="${spec#*|}"
        n="$(app_sql "$sql")"
        if [[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -gt 0 ]; then record PASS "$label" "$n lignes"
        else record FAIL "$label" "${n:-requête impossible}"; fi
    done
fi

check "Enregistrement de l'instance reçu par l'API de suivi" grep -q '/instances/register/' "$FAKE_TRACKING_LOG"
check "Installateur verrouillé après installation" test "$(http_code http://127.0.0.1:4567/)" = 403

scenario_checks

step "Fin du scénario $SCENARIO"
grep -c '^FAIL' "$RESULTS" >/dev/null && exit 1 || exit 0
