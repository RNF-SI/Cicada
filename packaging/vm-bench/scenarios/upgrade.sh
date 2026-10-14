# DESCRIPTION: Mise à jour : installe --from-deb (ancien paquet), crée des données, puis passe au paquet testé (dpkg -i, comme en prod)
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh.
#
# Usage : ./bench.sh run upgrade --from-deb ~/cicada-deb-0.1.47/cicada_0.1.47_amd64.deb
# Rejoue le flux de mise à jour du staging et de la prod : `dpkg -i` du nouveau
# paquet, le postinst met CICADA_VERSION à jour dans le .env puis relance
# `docker compose pull` + `up -d`. Les deux versions doivent différer (le
# postinst ne redéploie rien à version égale) et avoir leurs images sur GHCR.

. "$BENCH_DIR/scenarios/fresh-dockerdb.sh"

INITIAL_DEB="$BENCH_DIR/cicada-initial.deb"
[ -f "$INITIAL_DEB" ] || { echo "Scénario upgrade : --from-deb est obligatoire"; exit 1; }

TEMOIN_EMAIL="temoin@bench.test"
TEMOIN_PASSWORD="Temoin-Bench-1!"

login_code() {
    curl -s -o /dev/null -w '%{http_code}' --max-time 20 -H 'Content-Type: application/json' \
        -d "{\"username\":\"$1\",\"password\":\"$2\"}" "http://127.0.0.1:$FRONTEND_PORT/api/auth/login/"
}

scenario_checks() {
    local from to
    from="$(dpkg-deb -f "$INITIAL_DEB" Version)"
    to="$(dpkg-deb -f "$BENCH_DIR/cicada.deb" Version)"

    step "Données témoin avant mise à jour ($from)"
    docker exec cicada_prod_web python manage.py shell -c "
from apps.users.models import Role
Role.objects.create_user(email='$TEMOIN_EMAIL', password='$TEMOIN_PASSWORD',
                         nom_role='Temoin', prenom_role='Banc', active=True)
print('ok')" >/dev/null 2>&1
    # Vérifié en base : le frontend de l'ancienne version peut ne pas tourner
    check "Utilisateur témoin créé en $from" \
        test "$(app_sql "select count(*) from utilisateurs.t_roles where email='$TEMOIN_EMAIL'")" = 1

    # Instance configurée à la main selon l'ancien guide, avec une clé de dépôt
    # devenue invalide (cas des instances d'avant le changement de clé) : apt
    # refuse alors le dépôt. La mise à jour du paquet doit réparer cela seule.
    local keyring=/usr/share/keyrings/cicada-archive-keyring.gpg
    gpg --batch --quiet --homedir "$(mktemp -d)" --passphrase '' \
        --quick-gen-key "Ancienne cle <ancienne@bench.test>" rsa2048 sign 1d 2>/dev/null
    head -c 600 /dev/urandom > "$keyring"   # trousseau inutilisable
    echo "deb [signed-by=$keyring] https://apt.cicada.reserves-naturelles.org stable main" \
        > /etc/apt/sources.list.d/cicada.list
    local avant
    avant="$(apt-get update 2>&1)"   # capturé d'abord : grep -q + pipefail fausserait le test
    if echo "$avant" | grep -iE 'NO_PUBKEY|not signed|pas signé|^E:|^W:.*cicada' >/dev/null; then
        record INFO "Avant mise à jour : apt refuse le dépôt (clé invalide), comme attendu"
    else
        record INFO "Avant mise à jour : apt n'a pas signalé le dépôt (cas non reproduit)"
    fi

    step "Mise à jour $from → $to (dpkg -i)"
    local t0 out rc
    t0=$(date +%s)
    out="$(dpkg -i "$BENCH_DIR/cicada.deb" 2>&1)"; rc=$?
    echo "$out" | grep -E '===|\[(OK|WARN)\]' | sed 's/^/   /'
    if [ "$rc" -eq 0 ]; then record PASS "dpkg -i du nouveau paquet"
    else record FAIL "dpkg -i du nouveau paquet" "$(echo "$out" | tail -3)"; fi
    if echo "$out" | grep -q '\[WARN\]'; then
        record FAIL "Redéploiement de la stack par le postinst" "$(echo "$out" | grep '\[WARN\]' | head -2)"
    else
        record PASS "Redéploiement de la stack par le postinst"
    fi

    check "Source APT et clé fournies par le nouveau paquet" bash -c \
        'dpkg -S /etc/apt/sources.list.d/cicada.list /usr/share/keyrings/cicada-archive-keyring.gpg | grep -c "^cicada:" | grep -qx 2'
    local upd
    upd="$(apt-get update 2>&1)"
    if echo "$upd" | grep -iE 'NO_PUBKEY|not signed|pas signé|^E:|^W:.*cicada' >/dev/null; then
        record FAIL "Après mise à jour : apt accepte de nouveau le dépôt CICADA" "$(echo "$upd" | grep -iE 'cicada|NO_PUBKEY|^E:' | head -2)"
    else
        record PASS "Après mise à jour : apt accepte de nouveau le dépôt CICADA"
    fi
    check "CICADA_VERSION=$to dans le .env" test "$(env_value CICADA_VERSION)" = "$to"
    if wait_for 900 test "$(container_health cicada_prod_web)" = healthy; then
        record PASS "Conteneur web healthy après mise à jour" "$(( $(date +%s) - t0 ))s après dpkg -i"
    else
        record FAIL "Conteneur web healthy après mise à jour" "état : $(container_health cicada_prod_web)"
    fi
    local c tag
    for c in cicada_prod_web cicada_prod_frontend cicada_prod_celery_worker cicada_prod_celery_beat; do
        tag="$(docker inspect -f '{{.Config.Image}}' "$c" 2>/dev/null)"
        if [ "${tag##*:}" = "$to" ]; then record PASS "$c sur l'image $to"
        else record FAIL "$c sur l'image $to" "image : ${tag:-absent}"; fi
    done
    wait_for 120 test "$(http_code "http://127.0.0.1:$FRONTEND_PORT/")" = 200
    check "Frontend servi après mise à jour" test "$(http_code "http://127.0.0.1:$FRONTEND_PORT/")" = 200

    local pending
    pending="$(docker exec cicada_prod_web python manage.py showmigrations --plan 2>/dev/null | grep -c '^\[ \]')"
    check "Toutes les migrations appliquées" test "${pending:-x}" = 0
    check "Utilisateur témoin conservé (connexion)" test "$(login_code "$TEMOIN_EMAIL" "$TEMOIN_PASSWORD")" = 200
    check "Super-admin conservé (connexion)" test "$(login_code "$ADMIN_EMAIL" "$ADMIN_PASSWORD")" = 200

    # Les services systemd doivent tourner après la mise à jour, y compris
    # quand l'ancien paquet ne les avait pas démarrés (#222).
    local u
    for u in cicada-heartbeat.timer cicada-updater.path; do
        check "$u actif après mise à jour" systemctl is-active --quiet "$u"
    done
    check "Installateur toujours verrouillé" test "$(http_code http://127.0.0.1:4567/)" = 403
}
