# Contrôles « mise à jour sûre » (#796), partagés par upgrade-rollback et
# upgrade-rollback-external.
# shellcheck shell=bash
#
# Déroulé, sur une instance installée avec le paquet initial (--from-deb, une
# version publiée, donc son ANCIEN service de mise à jour) :
#  1. le bouton « Mettre à jour » demande la version testée, servie par un dépôt
#     APT local ; son backend a deux migrations ajoutées : la 1re crée une table
#     (validée), la 2e échoue → retour automatique, base d'avant, sans que
#     l'ancien service ne relance la nouvelle version derrière ;
#  2. `dpkg --configure -a` ne retente pas sans qu'on l'ait décidé ;
#  3. `cicada-update status` explique l'état sans l'application ;
#  4. cause corrigée (bon backend), `cicada-update retry` réussit ;
#  5. sauvegarde, restauration (tout ou rien), vérification ;
#  6. services (sauvegarde quotidienne, reprise au démarrage), bouton du nouveau
#     service.
# Le backend testé arrive par --backend-image (image non publiée) ; le frontend
# est celui de la version initiale, ré-étiqueté.

TEMOIN_EMAIL="temoin@bench.test"
TEMOIN_PASSWORD="Temoin-Bench-1!"
DEPOT=/srv/banc-depot

login_code() {
    curl -s -o /dev/null -w '%{http_code}' --max-time 20 -H 'Content-Type: application/json' \
        -d "{\"username\":\"$1\",\"password\":\"$2\"}" "http://127.0.0.1:$FRONTEND_PORT/api/auth/login/"
}
tentative() { python3 -c "import json;v=json.load(open('/var/lib/cicada/maintenance/tentative.json')).get('$1');print('' if v is None else v)" 2>/dev/null; }
resultat() { python3 -c "import json;v=json.load(open('/var/lib/cicada/updates/update_result.json')).get('$1');print('' if v is None else v)" 2>/dev/null; }
images_sur() {  # images_sur VERSION — les 4 conteneurs de l'application sur cette version
    local c tag
    for c in cicada_prod_web cicada_prod_frontend cicada_prod_celery_worker cicada_prod_celery_beat; do
        tag="$(docker inspect -f '{{.Config.Image}}' "$c" 2>/dev/null)"
        [ "${tag##*:}" = "$1" ] || { echo "$c : ${tag:-absent}"; return 1; }
    done
}
updater_termine() {
    local etat
    etat="$(systemctl show -p ActiveState --value cicada-updater.service)"
    [ "$etat" != activating ] && [ "$etat" != active ] && [ -f /var/lib/cicada/maintenance/tentative.json ] \
        && [ "$(tentative statut)" != en_cours ]
}

preparer_images() {  # preparer_images FROM TO
    local from="$1" to="$2" loaded last ctx
    step "Images de $to : backend local (--backend-image), frontend de $from ré-étiqueté"
    loaded="$(docker load -i "$BENCH_DIR/backend-image.tar" | sed -n 's/^Loaded image: //p' | tail -1)"
    docker tag "$loaded" cicada-backend:bon
    docker image inspect "ghcr.io/rnf-si/cicada-frontend:$from" >/dev/null 2>&1 \
        || docker pull -q "ghcr.io/rnf-si/cicada-frontend:$from" >/dev/null
    docker tag "ghcr.io/rnf-si/cicada-frontend:$from" "ghcr.io/rnf-si/cicada-frontend:$to"
    # Backend « cassé » : migrations à moitié passées (une validée, une en échec)
    last="$(docker run --rm --entrypoint ls cicada-backend:bon /app/apps/core/migrations \
            | grep -E '^[0-9]{4}_.*\.py$' | sort | tail -1)"
    ctx="$(mktemp -d)"
    cat > "$ctx/9998_banc_796_table.py" <<EOF
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [('core', '${last%.py}')]
    operations = [migrations.RunSQL('CREATE TABLE ccd_commons.banc_796 (id int)', 'DROP TABLE ccd_commons.banc_796')]
EOF
    cat > "$ctx/9999_banc_796_echec.py" <<'EOF'
from django.db import migrations


def echouer(apps, schema_editor):
    raise RuntimeError('migration du banc en échec (#796)')


class Migration(migrations.Migration):
    dependencies = [('core', '9998_banc_796_table')]
    operations = [migrations.RunPython(echouer, migrations.RunPython.noop)]
EOF
    printf 'FROM cicada-backend:bon\nCOPY 999*.py /app/apps/core/migrations/\n' > "$ctx/Dockerfile"
    if docker build -q -t "ghcr.io/rnf-si/cicada-backend:$to" "$ctx" >/dev/null; then
        record PASS "Backend $to dont une migration échoue (après une autre validée)"
    else
        record FAIL "Backend $to dont une migration échoue" "docker build"
    fi
    rm -rf "$ctx"
}

depot_local() {  # depot_local TO — dépôt APT servant le paquet testé
    step "Dépôt APT local : cicada $1"
    apt-get install -y -qq apt-utils >/dev/null 2>&1
    mkdir -p "$DEPOT"
    cp "$BENCH_DIR/cicada.deb" "$DEPOT/cicada_$1_amd64.deb"
    (cd "$DEPOT" && apt-ftparchive packages . > Packages)
    echo "deb [trusted=yes] file:$DEPOT ./" > /etc/apt/sources.list.d/banc-depot.list
    apt-get update -qq 2>/dev/null
    check "apt propose cicada $1" bash -c "apt-cache policy cicada | grep -qE '(Candidat|Candidate) *: *$1'"
}

maj_checks() {
    local from to out rc nom id
    from="$(dpkg-deb -f "$INITIAL_DEB" Version)"
    to="$(dpkg-deb -f "$BENCH_DIR/cicada.deb" Version)"
    [ -f "$BENCH_DIR/backend-image.tar" ] || { record FAIL "Image backend testée" "relancer avec --backend-image"; return; }

    step "Données témoin ($from)"
    docker exec cicada_prod_web python manage.py shell -c "
from apps.users.models import Role
Role.objects.create_user(email='$TEMOIN_EMAIL', password='$TEMOIN_PASSWORD',
                         nom_role='Temoin', prenom_role='Banc', active=True)
print('ok')" >/dev/null 2>&1
    check "Connexion du témoin en $from" test "$(login_code "$TEMOIN_EMAIL" "$TEMOIN_PASSWORD")" = 200

    preparer_images "$from" "$to"
    depot_local "$to"

    # ------------------------------------------------------------------
    step "Bouton « Mettre à jour » vers $to, traité par le service de mise à jour de $from"
    local t0=$SECONDS
    printf '{"version": "%s", "requested_by": "banc"}' "$to" > /var/lib/cicada/updates/update_trigger.json
    if wait_for 2700 updater_termine; then
        record PASS "Mise à jour terminée" "$(( SECONDS - t0 )) s"
    else
        record FAIL "Mise à jour terminée" "tentative : $(tentative statut) / $(tentative etape) ; updater : $(systemctl show -p ActiveState --value cicada-updater.service)"
    fi
    check "Retour automatique à $from (echec_retour_fait)" test "$(tentative statut)" = echec_retour_fait
    record INFO "Cause notée" "$(tentative cause)"
    check "La cause nomme la migration en échec" bash -c "grep -q 'migration du banc en échec' <<< \"\$1\"" _ "$(tentative cause)"
    check "CICADA_VERSION=$from dans le .env" test "$(env_value CICADA_VERSION)" = "$from"
    wait_for 300 test "$(container_health cicada_prod_web)" = healthy
    check "Les 4 conteneurs sur $from (l'ancien service n'a pas relancé $to)" images_sur "$from"
    wait_for 120 test "$(http_code "http://127.0.0.1:$FRONTEND_PORT/")" = 200
    check "Application servie" test "$(http_code "http://127.0.0.1:$FRONTEND_PORT/")" = 200
    check "Base d'avant : table de la migration validée retirée" \
        test "$(app_sql "select count(*) from pg_tables where tablename='banc_796'")" = 0
    check "Base d'avant : aucune migration du banc notée" \
        test "$(app_sql "select count(*) from utilisateurs.django_migrations where name like '999%banc_796%'")" = 0
    check "Témoin conservé (connexion)" test "$(login_code "$TEMOIN_EMAIL" "$TEMOIN_PASSWORD")" = 200
    check "Journal du conteneur en échec conservé" bash -c \
        "grep -l 'migration du banc en échec' /var/log/cicada/maj-*-cicada_prod_web.log"
    check "Sauvegarde d'avant la mise à jour gardée" test -f "$(tentative sauvegarde)/sauvegarde.json"
    check "Sauvegardes réservées à root" test "$(stat -c %a /var/backups/cicada)" = 700
    record INFO "État du paquet" "$(dpkg-query -W -f '${Status} ${Version}' cicada)"
    record INFO "Résultat écrit par l'ancien service" "$(head -c 200 /var/lib/cicada/updates/update_result.json)"

    step "dpkg --configure -a : pas de nouvelle tentative sans décision"
    id="$(tentative id)"
    out="$(dpkg --configure -a 2>&1)"; rc=$?
    echo "$out" | tail -4 | sed 's/^/   /'
    check "dpkg --configure -a réussit" test "$rc" = 0
    check "Aucune nouvelle tentative" test "$(tentative id)" = "$id"
    check "Toujours en $from" images_sur "$from"
    check "Paquet configuré" bash -c "dpkg-query -W -f '\${Status}' cicada | grep -q 'install ok installed'"

    step "État sans l'application : cicada-update status"
    out="$(cicada-update status 2>&1)"
    echo "$out" | sed 's/^/   /'
    check "Version en service affichée" bash -c "grep -q 'Version en service *: $from' <<< \"\$1\"" _ "$out"
    check "Nouvelle tentative proposée" bash -c "grep -q 'cicada-update retry' <<< \"\$1\"" _ "$out"

    # ------------------------------------------------------------------
    step "Cause corrigée, nouvelle tentative : cicada-update retry"
    docker tag cicada-backend:bon "ghcr.io/rnf-si/cicada-backend:$to"
    t0=$SECONDS
    out="$(cicada-update retry 2>&1)"; rc=$?
    echo "$out" | grep -E '===|✓|✗' | sed 's/^/   /'
    check "cicada-update retry réussit" test "$rc" = 0
    record INFO "Durée" "$(( SECONDS - t0 )) s"
    check "Les 4 conteneurs sur $to" images_sur "$to"
    check "CICADA_VERSION=$to" test "$(env_value CICADA_VERSION)" = "$to"
    check "Résultat lu par l'application : reussie" test "$(resultat statut)" = reussie
    local pending
    pending="$(docker exec cicada_prod_web python manage.py showmigrations --plan 2>/dev/null | grep -c '^\[ \]')"
    check "Toutes les migrations appliquées" test "${pending:-x}" = 0
    wait_for 120 test "$(http_code "http://127.0.0.1:$FRONTEND_PORT/")" = 200
    check "Témoin conservé (connexion)" test "$(login_code "$TEMOIN_EMAIL" "$TEMOIN_PASSWORD")" = 200
    check "Heartbeat : version en service annoncée ($to)" test "$(python3 -c \
        "import importlib.machinery as m; print(m.SourceFileLoader('hb', '/usr/bin/cicada-heartbeat').load_module().get_version())" 2>/dev/null)" = "$to"

    # ------------------------------------------------------------------
    step "Sauvegarde, restauration, vérification"
    out="$(cicada-backup 2>&1)"; rc=$?
    echo "$out" | tail -3 | sed 's/^/   /'
    check "cicada-backup" test "$rc" = 0
    nom="$(basename "$(echo "$out" | tail -1)")"
    check "Sauvegarde complète (base, fichiers, configuration)" python3 -c \
        "import json,sys;m=json.load(open('/var/backups/cicada/$nom/sauvegarde.json'));sys.exit(0 if m['ok'] and m['base'] and m['fichiers'] is not None and m['configuration'] else 1)"
    check "Configuration copiée lisible par root seul" test "$(stat -c %a "/var/backups/cicada/$nom/env")" = 600
    check "cicada-backup --verifier" cicada-backup --verifier "$nom"
    docker exec cicada_prod_web python manage.py shell -c "
from apps.users.models import Role
Role.objects.filter(email='$TEMOIN_EMAIL').update(email='modifie@bench.test')" >/dev/null 2>&1
    check "Témoin modifié après la sauvegarde" test "$(login_code "$TEMOIN_EMAIL" "$TEMOIN_PASSWORD")" != 200
    out="$(cicada-restore "$nom" 2>&1)"; rc=$?
    check "Restauration refusée sans --oui" bash -c "[ $rc -ne 0 ] && grep -q -- '--oui' <<< \"\$1\"" _ "$out"
    out="$(cicada-restore "$nom" --oui 2>&1)"; rc=$?
    echo "$out" | tail -3 | sed 's/^/   /'
    check "cicada-restore --oui" test "$rc" = 0
    wait_for 120 test "$(http_code "http://127.0.0.1:$FRONTEND_PORT/")" = 200
    check "Témoin rétabli (connexion)" test "$(login_code "$TEMOIN_EMAIL" "$TEMOIN_PASSWORD")" = 200
    check "Application en $to après la restauration" images_sur "$to"

    # ------------------------------------------------------------------
    step "Services du paquet"
    check "cicada-backup.timer actif" systemctl is-active --quiet cicada-backup.timer
    check "cicada-reprise.service activé au démarrage" systemctl is-enabled --quiet cicada-reprise.service
    check "Sauvegarde quotidienne (service)" systemctl start cicada-backup.service
    check "Sauvegarde quotidienne listée" bash -c "cicada-backup --liste | grep -q quotidienne"
    check "Résumé des sauvegardes lisible par l'application" bash -c \
        "docker exec cicada_prod_web python -c \"import json;print(json.load(open('/var/lib/cicada/backups.json'))['nombre'])\""

    step "Bouton, nouveau service : version déjà en service"
    rm -f /var/lib/cicada/updates/update_result.json
    printf '{"version": "%s", "requested_by": "banc"}' "$to" > /var/lib/cicada/updates/update_trigger.json
    wait_for 300 test -f /var/lib/cicada/updates/update_result.json
    check "Résultat : déjà à jour" test "$(resultat statut)" = a_jour
    check "Toujours en $to" images_sur "$to"
}
