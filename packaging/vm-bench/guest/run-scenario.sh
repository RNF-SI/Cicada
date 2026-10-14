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
# Paquet installé en premier. Par défaut le paquet testé ; un scénario de mise à
# jour installe d'abord un paquet plus ancien (--from-deb) et teste le passage.
INITIAL_DEB="$BENCH_DIR/cicada.deb"
# Message attendu si le formulaire DOIT refuser l'installation (scénario négatif)
EXPECT_REFUSAL=""
# Exploration fédérée : un scénario avec hub met FED_ENABLED=true
FED_ENABLED=false
FED_RELAY=false
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
  "federation_enabled": $FED_ENABLED,
  "federation_relay": $FED_RELAY,
  "federation_instance_id": "${BENCH_HUB_INSTANCE_ID:-}",
  "federation_instance_label": "${BENCH_HUB_INSTANCE_LABEL:-}",
  "federation_hub_url": "${BENCH_HUB_URL:-}",
  "federation_push_token": "${BENCH_HUB_PUSH:-}",
  "federation_read_token": "${BENCH_HUB_READ:-}",
  "rgpd_consent": false,
  $(scenario_db_answers)
}
EOF
}

# ---------------------------------------------------------------------------
step "Préparation de la VM"
. /etc/os-release
note "$PRETTY_NAME — noyau $(uname -r)"

# Le vrai domaine de suivi est toujours bloqué : un banc ne doit jamais
# enregistrer d'instance dans l'API de production.
echo "127.0.0.1 tracking.cicada.reserves-naturelles.org" >> /etc/hosts
: > "$FAKE_TRACKING_LOG"
if [ -n "${BENCH_TRACKING_IP:-}" ]; then
    # Serveur de suivi du banc (VM tracking) : API et dépôt APT sous leurs noms
    echo "$BENCH_TRACKING_IP tracking.cicada.bench apt.cicada.bench" >> /etc/hosts
    note "Serveur de suivi et dépôt APT : VM tracking ($BENCH_TRACKING_IP)"
else
systemd-run --quiet --unit=bench-fake-tracking python3 "$BENCH_DIR/guest/fake-tracking.py" "$FAKE_TRACKING_LOG" 8099
wait_for 10 curl -sf "$FAKE_TRACKING_URL/instances/version/" || note "fausse API de suivi injoignable"
# Surcharge par l'environnement des services, posée AVANT le paquet : on ne
# touche pas /etc/cicada/cicada.conf (conffile), sinon dpkg pose une question
# à la mise à jour. Les paquets antérieurs ignorent cette variable ; la vraie
# API reste alors bloquée par /etc/hosts.
for unit in cicada-installer.service cicada-heartbeat.service; do
    mkdir -p "/etc/systemd/system/$unit.d"
    printf '[Service]\nEnvironment=TRACKING_API_URL=%s\n' "$FAKE_TRACKING_URL" > "/etc/systemd/system/$unit.d/bench.conf"
done
systemctl daemon-reload
fi

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

# Contrôles qui portent sur le paquet installé en premier. Quand ce n'est pas
# le paquet testé (mise à jour), ses défauts connus sont consignés en INFO :
# ils décrivent l'ancienne version, pas celle qu'on valide.
if [ "$INITIAL_DEB" = "$BENCH_DIR/cicada.deb" ]; then
    pkg_record() { record "$@"; }
else
    pkg_record() { local s="$1"; [ "$s" = FAIL ] && s=INFO; record "$s" "[paquet initial] $2" "${3:-}"; }
fi
pkg_check() {
    local label="$1"; shift
    local out
    if out="$("$@" 2>&1)"; then pkg_record PASS "$label"
    else pkg_record FAIL "$label" "$(echo "$out" | tail -3)"; fi
}

# ---------------------------------------------------------------------------
step "Installation du paquet"
if [ -n "${BENCH_TRACKING_IP:-}" ]; then
    # Installation en une commande, telle que la donne le guide (install.sh
    # servi par le dépôt). Le socle du banc a déjà Docker : le script doit
    # s'en accommoder, comme sur un serveur où Docker est déjà installé.
    PKG_VERSION="$BENCH_TRACKING_FROM"
    INSTALL_CMD="curl -fsSL http://apt.cicada.bench/install.sh | bash -s -- --version $PKG_VERSION"
    note "$INSTALL_CMD"
    install_cicada() { curl -fsSL http://apt.cicada.bench/install.sh \
        | CICADA_APT_URL=http://apt.cicada.bench bash -s -- --version "$PKG_VERSION"; }
else
    PKG_VERSION="$(dpkg-deb -f "$INITIAL_DEB" Version)"
    install_cicada() { apt-get install -y "$INITIAL_DEB"; }
fi
note "cicada $PKG_VERSION"
if apt_out="$(install_cicada 2>&1)"; then
    record PASS "Installation du paquet (dépendances résolues)"
else
    echo "$apt_out" | tail -20
    record FAIL "Installation du paquet (dépendances résolues)" "$(echo "$apt_out" | grep -E '^E:|Dépend|Depends|Erreur' | head -3)"
    exit 1
fi
echo "$apt_out" | sed -n '/=====/,/=====/p'

if [ -n "${BENCH_TRACKING_IP:-}" ]; then
    check "install.sh annonce l'adresse du formulaire" \
        bash -c "echo \"\$0\" | grep -q ':4567'" "$apt_out"
fi
# Le paquet apporte lui-même la source APT et la clé du dépôt : aucune
# configuration manuelle pour recevoir les versions suivantes.
# (grep sans -q : avec pipefail, -q coupe dpkg-deb et fait échouer le pipeline)
if dpkg-deb -c "$BENCH_DIR/cicada.deb" | grep 'sources.list.d/cicada.list' >/dev/null; then
    pkg_check "Source APT et clé du dépôt fournies par le paquet" bash -c \
        'dpkg -S /etc/apt/sources.list.d/cicada.list /usr/share/keyrings/cicada-archive-keyring.gpg | grep -c "^cicada:" | grep -qx 2'
    if apt_upd="$(apt-get update 2>&1)" && ! echo "$apt_upd" | grep -iE 'NO_PUBKEY|not signed|pas signé|^Err|^E:|^W:.*cicada' >/dev/null; then
        pkg_record PASS "apt update accepte le dépôt CICADA sans configuration manuelle"
    else
        pkg_record FAIL "apt update accepte le dépôt CICADA sans configuration manuelle" \
            "$(echo "$apt_upd" | grep -iE 'cicada|NO_PUBKEY|sign|^E:' | head -2)"
    fi
fi

# #222 — l'installateur doit tourner sans intervention après l'installation
if wait_for 30 curl -sf http://127.0.0.1:4567/api/health; then
    pkg_record PASS "Installateur web démarré automatiquement (#222)"
else
    pkg_record FAIL "Installateur web démarré automatiquement (#222)" \
        "cicada-installer : $(systemctl is-active cicada-installer 2>&1) / $(systemctl is-enabled cicada-installer 2>&1)"
    note "contournement : systemctl start cicada-installer"
    systemctl start cicada-installer
    wait_for 30 curl -sf http://127.0.0.1:4567/api/health \
        || { record FAIL "Installateur web démarrable" "$(journalctl -u cicada-installer --no-pager | tail -5)"; exit 1; }
fi
check "Installateur joignable depuis le réseau (0.0.0.0:4567)" \
    curl -sf "http://$(hostname -I | awk '{print $1}'):4567/api/health"

for timer in cicada-heartbeat.timer cicada-updater.path; do
    pkg_check "$timer actif" systemctl is-active --quiet "$timer"
done

# Heartbeat (#226) : le service tourne avec le Python système
systemctl start cicada-heartbeat.service >/dev/null 2>&1
hb_rc=$?
hb_log="$(journalctl -u cicada-heartbeat.service --no-pager 2>&1 | tail -20)"
if echo "$hb_log" | grep -q "ModuleNotFoundError"; then
    pkg_record FAIL "Heartbeat exécutable (#226)" "$(echo "$hb_log" | grep ModuleNotFoundError | head -1)"
elif [ "$hb_rc" -ne 0 ]; then
    pkg_record FAIL "Heartbeat exécutable (#226)" "$(echo "$hb_log" | tail -2)"
else
    pkg_record PASS "Heartbeat exécutable (#226)"
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
# Ce que l'API de suivi sait de cette instance (vraie API : /instances/me/)
tracking_me() {
    curl -s --max-time 10 -H "X-Instance-Token: $(cat /etc/cicada/instance_token)" \
        http://tracking.cicada.bench/api/instances/me/
}
if [ -z "${BENCH_TRACKING_IP:-}" ]; then
    pkg_check "Heartbeat reçu par l'API de suivi" grep -q '/instances/heartbeat/' "$FAKE_TRACKING_LOG"
fi

# ---------------------------------------------------------------------------
if [ "${BENCH_MANUAL:-false}" = true ]; then
    # Mode manuel : tout est prêt, l'opérateur remplit le formulaire lui-même
    step "Mode manuel : à vous de jouer"
    exit 0
fi

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
if [ "$INITIAL_DEB" != "$BENCH_DIR/cicada.deb" ]; then
    # Les installateurs antérieurs peuvent rendre la main avant que web soit
    # healthy (santé mal détectée) : attendre, sinon les contrôles tombent trop tôt.
    wait_for 900 test "$(container_health cicada_prod_web)" = healthy
    wait_for 120 test "$(http_code "http://127.0.0.1:$FRONTEND_PORT/")" = 200
fi

resp_get() { python3 -c "import json,sys;d=json.load(open('$BENCH_DIR/install-response.json'));v=d.get('$1');print('' if v is None else v if not isinstance(v,list) else '; '.join(v))" 2>/dev/null; }
# Dernière ligne significative d'une erreur (souvent une trace Python entière)
last_line() { grep -v '^[[:space:]]*$' | grep -v '^[[:space:]]*\^' | tail -1 | cut -c1-300; }

if [ -n "$EXPECT_REFUSAL" ]; then
    # Scénario négatif : un refus clair et immédiat, rien de démarré
    if [ "$(resp_get success)" = "True" ]; then
        record FAIL "Installation refusée" "le formulaire a accepté"
    elif resp_get error | grep -q "$EXPECT_REFUSAL"; then
        record PASS "Installation refusée avec explication" "« $EXPECT_REFUSAL »"
    else
        record FAIL "Installation refusée avec explication" "$( { resp_get error; resp_get errors; } | last_line)"
    fi
    check "Refus immédiat (moins de 60 s)" test "$duration" -lt 60
    check "Rien n'a été démarré (pas de .env, pas de conteneur web)" \
        bash -c '[ ! -f /var/lib/cicada/.env ] && ! docker ps -a --format "{{.Names}}" | grep -qx cicada_prod_web'
    scenario_checks
    step "Fin du scénario $SCENARIO"
    grep -q '^FAIL' "$RESULTS" && exit 1 || exit 0
fi

if [ "$curl_rc" -eq 0 ] && [ "$(resp_get success)" = "True" ]; then
    pkg_record PASS "Installation déclarée réussie par le formulaire"
else
    pkg_record FAIL "Installation déclarée réussie par le formulaire" \
        "$( { resp_get error; resp_get errors; } | last_line)"
    echo "---- Réponse complète de l'installateur ----"
    resp_get error
    resp_get errors
fi

redirect="$(resp_get redirect_url)"
if [ "$redirect" = "$EXPECTED_URL" ]; then
    pkg_record PASS "Redirection finale vers l'URL publique" "$redirect"
else
    pkg_record FAIL "Redirection finale vers l'URL publique (#223)" "obtenu « ${redirect:-rien} », attendu « $EXPECTED_URL »"
fi

# ---------------------------------------------------------------------------
step "Contrôles de l'instance"
pkg_check "Conteneur web healthy" test "$(container_health cicada_prod_web)" = healthy
for c in cicada_prod_frontend cicada_prod_celery_worker cicada_prod_celery_beat cicada_prod_redis; do
    state="$(container_health "$c")"
    case "$state" in running|healthy) pkg_record PASS "Conteneur $c démarré" ;;
                     *) pkg_record FAIL "Conteneur $c démarré" "état : ${state:-absent}" ;; esac
done

pkg_check "Frontend servi sur :$FRONTEND_PORT" test "$(http_code "http://127.0.0.1:$FRONTEND_PORT/")" = 200
if curl -s -D - -o /dev/null --max-time 10 "http://127.0.0.1:$FRONTEND_PORT/api/health/" | grep -qi '^x-correlation-id'; then
    pkg_record PASS "API CICADA joignable via le frontend (/api/health/)"
else
    pkg_record FAIL "API CICADA joignable via le frontend (/api/health/)" "code $(http_code "http://127.0.0.1:$FRONTEND_PORT/api/health/")"
fi

login_code="$(curl -s -o "$BENCH_DIR/login.json" -w '%{http_code}' --max-time 20 \
    -H 'Content-Type: application/json' -H "Host: $DOMAIN" \
    -d "{\"username\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
    "http://127.0.0.1:$FRONTEND_PORT/api/auth/login/")"
if [ "$login_code" = 200 ] && grep -q '"access"' "$BENCH_DIR/login.json"; then
    pkg_record PASS "Connexion du super-admin créé par le formulaire"
else
    pkg_record FAIL "Connexion du super-admin créé par le formulaire" "HTTP $login_code $(head -c 200 "$BENCH_DIR/login.json" 2>/dev/null)"
fi

if [ "$(container_health cicada_prod_web)" = healthy ]; then
    for spec in \
        "Nomenclatures importées|select count(*) from ref_nomenclatures.t_nomenclatures" \
        "HabRef importé|select count(*) from ref_habitats.habref" \
        "TaxRef importé|select count(*) from taxonomie.taxref" \
        "Découpage administratif importé|select count(*) from ref_geo.l_areas"; do
        label="${spec%%|*}"; sql="${spec#*|}"
        n="$(app_sql "$sql")"
        if [[ "$n" =~ ^[0-9]+$ ]] && [ "$n" -gt 0 ]; then pkg_record PASS "$label" "$n lignes"
        else pkg_record FAIL "$label" "${n:-requête impossible}"; fi
    done
fi

if [ -n "${BENCH_TRACKING_IP:-}" ]; then
    pkg_check "Instance enregistrée dans l'API de suivi (instances/me)" \
        bash -c "curl -s --max-time 10 -H \"X-Instance-Token: \$(cat /etc/cicada/instance_token)\" http://tracking.cicada.bench/api/instances/me/ | grep -q '\"version\"'"
else
    pkg_check "Enregistrement de l'instance reçu par l'API de suivi" grep -q '/instances/register/' "$FAKE_TRACKING_LOG"
fi
pkg_check ".env (secrets) lisible par root seul" test "$(stat -c %a /var/lib/cicada/.env)" = 600
pkg_check "Installateur verrouillé après installation" test "$(http_code http://127.0.0.1:4567/)" = 403

scenario_checks

step "Fin du scénario $SCENARIO"
grep -c '^FAIL' "$RESULTS" >/dev/null && exit 1 || exit 0
