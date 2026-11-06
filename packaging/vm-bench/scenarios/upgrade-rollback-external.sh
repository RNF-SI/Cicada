# DESCRIPTION: Mise à jour sûre (#796), PostgreSQL existant (compte sans super-utilisateur) : même déroulé que upgrade-rollback
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh. Mêmes options que upgrade-rollback.
#
# La base est celle d'un PostgreSQL installé hors Docker, préparé par
# cicada-prepare-db : le compte de l'application n'est que propriétaire de la
# base. La sauvegarde et la restauration (tout ou rien) passent par lui.

. "$BENCH_DIR/scenarios/external-db-localhost.sh"
. "$BENCH_DIR/scenarios/commun/maj-checks.sh"

INITIAL_DEB="$BENCH_DIR/cicada-initial.deb"
[ -f "$INITIAL_DEB" ] || { echo "Scénario upgrade-rollback-external : --from-deb est obligatoire"; exit 1; }

eval "$(declare -f scenario_checks | sed '1s/scenario_checks/base_existante_checks/')"

scenario_checks() {
    base_existante_checks
    check "Compte de l'application sans super-utilisateur" \
        test "$(pg "select rolsuper from pg_roles where rolname='$DB_USER'")" = f
    maj_checks
}
