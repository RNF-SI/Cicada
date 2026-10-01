# DESCRIPTION: Serveur de suivi + dépôt APT (TrackingCicada) : apt install depuis le dépôt, enregistrement, heartbeat, mise à jour « un clic »
# TRACKING_VM: oui
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh.
#
# Reproduit le cycle de vie d'une instance face au serveur TrackingCicada :
#   1. installation par `apt install cicada` depuis le dépôt signé (guide, étape 1-2) ;
#   2. enregistrement auprès de la vraie API de suivi (formulaire) ;
#   3. heartbeat (timer nocturne) : l'API annonce la dernière version ;
#   4. release : la nouvelle version est publiée dans le dépôt ;
#   5. l'administrateur clique « Mettre à jour » : l'updater fait apt + Docker ;
#   6. le heartbeat suivant remonte la nouvelle version.
# Base de données dans Docker : ce scénario porte sur le suivi et le dépôt.

. "$BENCH_DIR/scenarios/fresh-dockerdb.sh"

. "$BENCH_DIR/scenarios/lib/tracking-checks.sh"

scenario_checks() {
    check "Conteneur base de données healthy" test "$(container_health cicada_prod_db)" = healthy
    tracking_suivi_checks
    tracking_maj_checks
}
