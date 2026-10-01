# DESCRIPTION: De A à Z sur 4 VM : dépôt APT + suivi, base sur serveur séparé, hub — installation, heartbeat, mise à jour par le bouton, publication fédérée
# DB_VM: oui
# HUB_VM: oui
# TRACKING_VM: oui
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh (VM CICADA) et guest/db-side.sh (VM base).
#
# L'infrastructure RNF complète, dans l'ordre de la vraie vie :
#   1. `apt install cicada` (version initiale) depuis le dépôt de TrackingCicada ;
#   2. formulaire : base sur le serveur de bases (préparée par son admin),
#      hub renseigné (jetons d'enroler_instance), relais activé ;
#   3. enregistrement et heartbeat auprès de l'API de suivi ;
#   4. release : nouvelle version publiée, bouton « Mettre à jour » ;
#   5. après la mise à jour seulement, publication vers le hub (la version
#      initiale ne sait pas encore publier) et recherche relayée.

. "$BENCH_DIR/scenarios/external-db-remote.sh"
. "$BENCH_DIR/scenarios/lib/tracking-checks.sh"
. "$BENCH_DIR/scenarios/lib/federation-checks.sh"

FED_ENABLED=true
FED_RELAY=true

eval "remote_$(declare -f scenario_checks)"

scenario_checks() {
    remote_scenario_checks
    tracking_suivi_checks
    tracking_maj_checks
    federation_checks
}
