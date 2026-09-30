# Bibliothèque commune aux scripts exécutés DANS la VM (en root).
# shellcheck shell=bash

BENCH_DIR="${BENCH_DIR:-/home/ubuntu/bench}"
RESULTS="$BENCH_DIR/results.tsv"
FAKE_TRACKING_URL="http://127.0.0.1:8099/api"
FAKE_TRACKING_LOG="$BENCH_DIR/fake-tracking.log"

C_RED='\033[0;31m'; C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'; C_BLUE='\033[0;34m'; C_NC='\033[0m'

step() { echo -e "\n${C_BLUE}── $* ${C_NC}"; }
note() { echo -e "   ${C_YELLOW}·${C_NC} $*"; }

# Enregistre un contrôle. Usage : record PASS|FAIL|INFO "libellé" "détail"
record() {
    local status="$1" label="$2" detail="${3:-}"
    printf '%s\t%s\t%s\n' "$status" "$label" "${detail//$'\n'/ }" >> "$RESULTS"
    case "$status" in
        PASS) echo -e "   ${C_GREEN}✓${C_NC} $label${detail:+ — $detail}" ;;
        FAIL) echo -e "   ${C_RED}✗ $label${C_NC}${detail:+ — $detail}" ;;
        *)    echo -e "   ${C_BLUE}i${C_NC} $label${detail:+ — $detail}" ;;
    esac
}

# check "libellé" commande… : PASS si la commande réussit, FAIL sinon.
check() {
    local label="$1"; shift
    local out
    if out="$("$@" 2>&1)"; then
        record PASS "$label"
    else
        record FAIL "$label" "$(echo "$out" | tail -3)"
    fi
}

# Attend qu'une commande réussisse. Usage : wait_for SECONDES commande…
wait_for() {
    local timeout="$1"; shift
    local waited=0
    until "$@" >/dev/null 2>&1; do
        sleep 2; waited=$((waited + 2))
        [ "$waited" -ge "$timeout" ] && return 1
    done
    return 0
}

http_code() { curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$@"; }

env_value() { awk -F= -v k="$1" '$1==k{sub(/^[^=]*=/,""); print; exit}' /var/lib/cicada/.env 2>/dev/null; }

container_health() { docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$1" 2>/dev/null; }

# Requête SQL exécutée PAR l'application (mêmes identifiants, même réseau que Django).
app_sql() {
    docker exec cicada_prod_web python manage.py shell -c \
        "from django.db import connection
c = connection.cursor(); c.execute(\"\"\"$1\"\"\"); print(c.fetchone()[0])" 2>/dev/null | tail -1
}
