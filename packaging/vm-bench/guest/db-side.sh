#!/bin/bash
# Exécuté sur la VM « serveur de base », pendant que l'installateur de CICADA
# attend : appelle la fonction db_server_prepare du scénario (ce que fait
# l'administrateur de la base, en terminal, sur SA machine). Ce qu'elle écrit
# dans base-prete (ex. le mot de passe affiché) est remis à la VM CICADA.
# Résultats dans results.tsv de cette VM, fusionnés par bench.sh.
set -uo pipefail
SCENARIO="$1"; CICADA_IP="$2"
BENCH_DIR="${BENCH_DIR:-/home/ubuntu/bench}"
. "$BENCH_DIR/guest/lib.sh"
: > "$RESULTS"
: > "$BENCH_DIR/base-prete"
. "$BENCH_DIR/guest/prereq-postgres.sh"
db_server_prepare() { :; }
. "$BENCH_DIR/scenarios/$SCENARIO.sh"
# La VM vient de démarrer : attendre que PostgreSQL accepte les connexions
wait_for 120 sudo -u postgres psql -Atc 'select 1' || echo "PostgreSQL ne répond pas"
step "Serveur de base : préparation pour CICADA ($CICADA_IP)"
db_server_prepare "$CICADA_IP"
