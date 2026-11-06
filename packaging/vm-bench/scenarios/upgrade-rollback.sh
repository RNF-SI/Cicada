# DESCRIPTION: Mise à jour sûre (#796), base en conteneur : bouton de l'ancien service → migration en échec → retour automatique ; retry, sauvegarde, restauration
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh.
#
#   docker build -f backend/Dockerfile.prod --build-arg CICADA_VERSION=0.1.70 -t cicada-backend:local backend
#   docker save cicada-backend:local -o /tmp/backend.tar
#   (cd packaging && VERSION=0.1.70 ./build-deb.sh)
#   ./bench.sh run upgrade-rollback --from-deb ~/cicada_0.1.69_amd64.deb \
#       --deb ../build/cicada_0.1.70_amd64.deb --backend-image /tmp/backend.tar
#
# --from-deb : une version publiée (son service de mise à jour est celui
# d'avant #796, c'est lui qui traite le premier clic sur chaque instance).

. "$BENCH_DIR/scenarios/fresh-dockerdb.sh"
. "$BENCH_DIR/scenarios/commun/maj-checks.sh"

INITIAL_DEB="$BENCH_DIR/cicada-initial.deb"
[ -f "$INITIAL_DEB" ] || { echo "Scénario upgrade-rollback : --from-deb est obligatoire"; exit 1; }

scenario_checks() {
    check "Conteneur base de données healthy" test "$(container_health cicada_prod_db)" = healthy
    maj_checks
}
