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

. "$BENCH_DIR/scenarios/lib/federation-checks.sh"

# Contrôles de base distante, repris tels quels
eval "remote_$(declare -f scenario_checks)"

scenario_checks() {
    remote_scenario_checks
    federation_checks
}

