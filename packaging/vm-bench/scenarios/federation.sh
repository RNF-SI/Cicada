# DESCRIPTION: De A à Z : base sur un serveur séparé + hub d'exploration fédérée (3 VM) — installation, consentement, publication, recherche relayée
# DB_VM: oui
# HUB_VM: oui
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh (VM CICADA) et guest/db-side.sh (VM base).
#
# Reprend external-db-remote (topologie RNF) et raccorde l'instance à un hub
# déployé selon docs/DEPLOIEMENT_HUB.md sur une 3e VM. Les jetons délivrés par
# enroler_instance sont saisis dans la section « Exploration fédérée » du
# formulaire, relais activé (l'exploration de l'instance est servie par le hub).

. "$BENCH_DIR/scenarios/external-db-remote.sh"

FED_ENABLED=true
FED_RELAY=true

# Contrôles de base distante, repris tels quels
eval "remote_$(declare -f scenario_checks)"

web_manage() { docker exec cicada_prod_web python manage.py "$@" 2>&1; }

# Appel authentifié à l'API de l'instance (super-admin du formulaire), via le frontend
api_get() {
    local access
    access="$(curl -s --max-time 20 -H 'Content-Type: application/json' \
        -d "{\"username\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" \
        "http://127.0.0.1:$FRONTEND_PORT/api/auth/login/" \
        | python3 -c 'import json,sys;print(json.load(sys.stdin).get("access",""))' 2>/dev/null)"
    curl -s --max-time 30 -H "Authorization: Bearer $access" "http://127.0.0.1:$FRONTEND_PORT$1"
}

scenario_checks() {
    remote_scenario_checks

    step "Raccordement au hub ($BENCH_HUB_URL)"
    if [ -z "${BENCH_HUB_PUSH:-}" ]; then
        record FAIL "Jetons du hub disponibles" "enrôlement échoué (voir hub-server.log)"
        return
    fi
    check "Formulaire : hub et jetons écrits dans le .env" \
        bash -c "grep -qx 'CICADA_HUB_URL=$BENCH_HUB_URL' /var/lib/cicada/.env && grep -qx 'CICADA_HUB_PUSH_TOKEN=$BENCH_HUB_PUSH' /var/lib/cicada/.env"
    check "Formulaire : exploration servie par le hub (relais)" \
        grep -qx 'CICADA_EXPLORATION_SOURCE=hub' /var/lib/cicada/.env

    step "Publication"
    # Sans consentement de la structure, rien ne sort (réglage faux par défaut)
    local out
    out="$(web_manage push_federation)"
    if echo "$out" | grep -q "partage avec l'exploration nationale est désactivé"; then
        record PASS "Publication refusée tant que la structure n'a pas consenti"
    else
        record FAIL "Publication refusée tant que la structure n'a pas consenti" "$(echo "$out" | tail -2)"
    fi

    # Des plans validés à publier (jeu de test), indexés
    out="$(web_manage seed_testdata --only=plans)"; record INFO "Jeu de test (plans)" "$(echo "$out" | tail -1)"
    out="$(web_manage rebuild_search_index)"; record INFO "Index de recherche" "$(echo "$out" | tail -1)"

    # Consentement : case « partage » des paramètres d'administration
    web_manage shell -c "from apps.core.models import SiteConfiguration as S
c = S.get_instance(); c.federation_partage = True; c.save()" >/dev/null
    local rc
    out="$(web_manage push_federation)"; rc=$?
    echo "$out" | sed 's/\x1b\[[0-9;]*m//g' | sed 's/^/   /' | tail -8
    if [ "$rc" -eq 0 ]; then
        record PASS "push_federation (dépôt complet puis bascule)" "$(echo "$out" | grep -oE '[0-9]+ plan\(s\)[^.]*' | head -1)"
    else
        record FAIL "push_federation" "$(echo "$out" | sed 's/\x1b\[[0-9;]*m//g' | tail -2)"
    fi

    step "Vérifications côté hub"
    local etat
    etat="$(curl -s --max-time 20 -H "X-Hub-Token: $BENCH_HUB_READ" "$BENCH_HUB_URL/api/federation/instances/")"
    echo "$etat" > "$BENCH_DIR/hub-instances.json"
    local plans_hub
    plans_hub="$(python3 - "$BENCH_HUB_INSTANCE_ID" <<'PY' 2>/dev/null
import json, sys
data = json.load(open('/home/ubuntu/bench/hub-instances.json'))
rows = data if isinstance(data, list) else data.get('results') or data.get('instances') or []
for r in rows:
    if r.get('instance_id') == sys.argv[1] or r.get('identifiant') == sys.argv[1]:
        n = next((v for k, v in r.items() if 'plan' in k and isinstance(v, int)), 0)
        print(n); break
PY
)"
    if [[ "$plans_hub" =~ ^[0-9]+$ ]] && [ "$plans_hub" -gt 0 ]; then
        record PASS "Le hub a reçu les plans de l'instance" "$plans_hub plan(s)"
    else
        record FAIL "Le hub a reçu les plans de l'instance" "$(head -c 300 "$BENCH_DIR/hub-instances.json")"
    fi

    step "Exploration de l'instance, relayée par le hub"
    # Provenance (instance_libelle) et liste des structures sont postérieures à
    # 0.1.49 : exigées seulement des images qui les contiennent.
    local image_version recentes=false
    image_version="$(env_value CICADA_VERSION)"
    [ "$(printf '%s\n0.1.49\n' "$image_version" | sort -V | tail -1)" != 0.1.49 ] && recentes=true
    record_recent() {  # record_recent PASS|FAIL libellé détail
        if [ "$1" = FAIL ] && [ "$recentes" = false ]; then
            record INFO "$2 (absent de l'image $image_version)" "${3:-}"
        else
            record "$@"
        fi
    }

    local recherche n_hub n_prov
    recherche="$(api_get '/api/exploration/plans/?q=Camargue')"
    echo "$recherche" > "$BENCH_DIR/recherche.json"
    read -r n_hub n_prov < <(python3 -c "
import json
d = json.load(open('$BENCH_DIR/recherche.json'))
rows = d if isinstance(d, list) else d.get('results', [])
# Seul le hub préfixe la référence par l'instance et ajoute url_instance
hub = [r for r in rows if str(r.get('reference', '')).startswith('$BENCH_HUB_INSTANCE_ID:') and 'url_instance' in r]
print(len(hub), sum(1 for r in rows if r.get('instance_libelle')))" 2>/dev/null || echo "0 0")
    if [ "${n_hub:-0}" -gt 0 ]; then
        record PASS "Recherche « Camargue » servie par le hub (relais)" "$n_hub plan(s) « $BENCH_HUB_INSTANCE_ID:… »"
    else
        record FAIL "Recherche « Camargue » servie par le hub (relais)" "$(head -c 300 "$BENCH_DIR/recherche.json")"
    fi
    if [ "${n_prov:-0}" -gt 0 ]; then
        record PASS "Provenance affichable (instance_libelle)" "$n_prov plan(s)"
    else
        record_recent FAIL "Provenance affichable (instance_libelle)" "aucun résultat ne la porte"
    fi

    local instances
    instances="$(api_get /api/exploration/instances/)"
    if echo "$instances" | python3 -c 'import json,sys;print(json.load(sys.stdin))' 2>/dev/null | grep -q "$BENCH_HUB_INSTANCE_LABEL"; then
        record PASS "« Structures d'origine » servies par le hub" "$BENCH_HUB_INSTANCE_LABEL"
    else
        record_recent FAIL "« Structures d'origine » servies par le hub" "$(echo "$instances" | tr -d '\n' | head -c 120)"
    fi
}
