# DESCRIPTION: Labo persistant (via « ./bench.sh labo ») : infrastructure complète installée puis laissée allumée, sans mise à jour
# DB_VM: oui
# HUB_VM: oui
# TRACKING_VM: oui
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh (VM CICADA) et guest/db-side.sh (VM base).
#
# Comme a-z, mais s'arrête une fois l'instance installée, enregistrée et son
# premier heartbeat parti : la suite (releases, bouton « Mettre à jour »,
# publication vers le hub) se joue à la main, sur la durée, avec
# ./bench.sh labo publier|heartbeat|hub|statut.

. "$BENCH_DIR/scenarios/external-db-remote.sh"
. "$BENCH_DIR/scenarios/commun/tracking-checks.sh"

FED_ENABLED=true
FED_RELAY=true
# Domaine = adresse de la VM : l'application s'ouvre directement depuis le
# navigateur de l'hôte (http://<ip>:8080), sans toucher à son /etc/hosts.
DOMAIN="$(hostname -I | awk '{print $1}')"
# (fichier aussi lu sur le serveur de base, où FRONTEND_PORT n'existe pas)
EXPECTED_URL="http://$DOMAIN:${FRONTEND_PORT:-8080}"

eval "remote_$(declare -f scenario_checks)"

scenario_checks() {
    remote_scenario_checks
    tracking_suivi_checks
}
