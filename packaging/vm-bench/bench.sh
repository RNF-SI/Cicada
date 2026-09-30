#!/bin/bash
# =============================================================================
# Banc de test de l'installateur CICADA en VM (Multipass)
#
# Rejoue une installation complète du paquet .deb sur un système neuf, comme
# le ferait un opérateur, puis vérifie le résultat. Le formulaire web est piloté
# par son API (POST :4567/api/install) : pas de navigateur, donc automatisable.
#
# Usage :
#   ./bench.sh list                         # scénarios disponibles
#   ./bench.sh run <scenario> [options]     # jouer un scénario
#   ./bench.sh base [--os debian12] [--rebuild]   # (re)construire la VM de base
#   ./bench.sh shell [--os …]               # shell dans la VM (état du dernier run)
#   ./bench.sh clean [--all]                # arrêter les VM (--all : les supprimer)
#
# Options de run :
#   --os debian12|debian13|ubuntu24   système cible (défaut : debian12)
#   --deb CHEMIN      .deb à tester (défaut : construit depuis l'arbre courant)
#   --keep            laisser la VM allumée après le run (pour inspecter)
#   --no-degraded     ne pas simuler un serveur « degraded » (voir guest/run-scenario.sh)
#   --no-prepull      ne pas pré-télécharger les images Docker dans la base
#
# Les résultats vont dans packaging/vm-bench/results/<date>-<scenario>-<os>/.
# Code retour : 0 si tous les contrôles passent, 1 sinon.
# =============================================================================
set -euo pipefail

BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGING_DIR="$(cd "$BENCH_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$PACKAGING_DIR/.." && pwd)"

OS="debian12"
DEB=""
KEEP=false
DEGRADED=true
PREPULL=true
REBUILD=false
ALL=false

VM_CPUS=4
VM_MEMORY=6G
VM_DISK=30G
GUEST_DIR=/home/ubuntu/bench

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info()  { echo -e "${BLUE}[bench]${NC} $*"; }
warn()  { echo -e "${YELLOW}[bench]${NC} $*"; }
die()   { echo -e "${RED}[bench] $*${NC}" >&2; exit 2; }

image_for_os() {
    case "$1" in
        debian12) echo "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2" ;;
        debian13) echo "https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2" ;;
        ubuntu24) echo "24.04" ;;
        *) die "OS inconnu : $1 (debian12, debian13, ubuntu24)" ;;
    esac
}

usage() { sed -n '2,/^# =====/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 0; }

list_scenarios() {
    for f in "$BENCH_DIR"/scenarios/*.sh; do
        printf "  %-26s %s\n" "$(basename "$f" .sh)" "$(sed -n 's/^# DESCRIPTION: //p' "$f")"
    done
}

# Les images cloud Debian sont téléchargées une fois dans images/ puis lancées
# depuis le fichier : multipass abandonne sur la moindre lenteur du miroir.
# (Pas de dossier caché : le snap multipass ne lit pas les dossiers en « . ».)
launch_source() {
    local src; src="$(image_for_os "$OS")"
    case "$src" in
        http*)
            local file="$BENCH_DIR/images/$(basename "$src")"
            mkdir -p "$BENCH_DIR/images"
            if [ ! -f "$file" ] || [ "$(find "$file" -mtime +14 2>/dev/null)" ]; then
                info "Téléchargement de $(basename "$src")" >&2
                curl -fsSL --retry 5 --retry-delay 3 -C - -o "$file.part" "$src" >&2 && mv "$file.part" "$file"
            fi
            echo "file://$file" ;;
        *) echo "$src" ;;
    esac
}

vm_exists() { multipass info "$1" >/dev/null 2>&1; }
vm_state()  { multipass info "$1" --format csv 2>/dev/null | awk -F, 'NR==2{print $2}'; }

# Exécute une commande root dans la VM.
vx() { local vm="$1"; shift; multipass exec "$vm" -- sudo "$@"; }

push_guest_scripts() {
    local vm="$1"
    multipass exec "$vm" -- rm -rf "$GUEST_DIR"
    multipass exec "$vm" -- mkdir -p "$GUEST_DIR"
    multipass transfer -r "$BENCH_DIR/guest" "$vm:$GUEST_DIR/"
    multipass transfer -r "$BENCH_DIR/scenarios" "$vm:$GUEST_DIR/"
}

# --- VM de base : OS + prérequis documentés (Docker) + images pré-tirées ---
# Une seule VM par OS, figée dans l'instantané « socle » et restaurée avant
# chaque scénario : on ne repaie ni le boot cloud-init, ni l'installation de
# Docker, ni le téléchargement de ~2 Go d'images. (Pas de `multipass clone` :
# il échoue sur les VM lancées depuis un fichier image, cas des images Debian.)
# Conséquence : les scénarios d'un même OS se jouent l'un après l'autre.
build_base() {
    local base="ccd-base-$OS"
    if vm_exists "$base"; then
        if [ "$REBUILD" = true ]; then
            info "Suppression de l'ancienne base $base"
            multipass delete --purge "$base"
        else
            info "Base $base déjà présente (--rebuild pour la refaire)"
            return 0
        fi
    fi
    local source; source="$(launch_source)"
    info "Création de la VM de base $base ($source)"
    multipass launch "$source" --name "$base" \
        --cpus "$VM_CPUS" --memory "$VM_MEMORY" --disk "$VM_DISK" --timeout 900
    push_guest_scripts "$base"
    info "Installation des prérequis Docker (procédure du guide d'installation)"
    vx "$base" bash "$GUEST_DIR/guest/prereq-docker.sh"
    if [ "$PREPULL" = true ]; then
        local version; version="$(tr -d '[:space:]' < "$PROJECT_ROOT/version.txt")"
        info "Pré-téléchargement des images Docker $version"
        vx "$base" bash "$GUEST_DIR/guest/prepull-images.sh" "$version"
    fi
    multipass stop "$base"
    multipass snapshot "$base" --name socle >/dev/null
    info "Base $base prête (instantané « socle »)"
}

build_deb() {
    if [ -n "$DEB" ]; then
        [ -f "$DEB" ] || die ".deb introuvable : $DEB"
        return 0
    fi
    info "Construction du .deb depuis l'arbre courant"
    (cd "$PACKAGING_DIR" && ./build-deb.sh >/dev/null)
    DEB="$(ls -t "$PACKAGING_DIR"/build/cicada_*_amd64.deb | head -1)"
    info "Paquet : $(basename "$DEB")"
}

run_scenario() {
    local scenario="$1"
    local scenario_file="$BENCH_DIR/scenarios/$scenario.sh"
    [ -f "$scenario_file" ] || { list_scenarios; die "Scénario inconnu : $scenario"; }

    local vm="ccd-base-$OS"
    local stamp; stamp="$(date +%Y%m%d-%H%M%S)"
    local out="$BENCH_DIR/results/$stamp-$scenario-$OS"
    mkdir -p "$out"

    build_deb
    build_base

    info "Restauration de l'instantané socle de $vm"
    [ "$(vm_state "$vm")" = Stopped ] || multipass stop --force "$vm"
    multipass restore --destructive "$vm.socle" >/dev/null
    multipass start "$vm"

    push_guest_scripts "$vm"
    multipass transfer "$DEB" "$vm:$GUEST_DIR/cicada.deb"

    info "Scénario $scenario sur $OS — journal : $out/run.log"
    local rc
    set +e
    multipass exec "$vm" -- sudo env \
        BENCH_DEGRADED="$DEGRADED" BENCH_OS="$OS" BENCH_DIR="$GUEST_DIR" \
        bash "$GUEST_DIR/guest/run-scenario.sh" "$scenario" 2>&1 | tee "$out/run.log"
    rc=${PIPESTATUS[0]}
    set -e

    # Artefacts utiles au diagnostic, même en cas d'échec
    multipass transfer "$vm:$GUEST_DIR/results.tsv" "$out/results.tsv" 2>/dev/null || true
    vx "$vm" bash "$GUEST_DIR/guest/collect.sh" > "$out/diagnostic.txt" 2>&1 || true

    if [ -f "$out/results.tsv" ]; then
        local pass fail
        pass=$(awk -F'\t' '$1=="PASS"' "$out/results.tsv" | wc -l)
        fail=$(awk -F'\t' '$1=="FAIL"' "$out/results.tsv" | wc -l)
        echo
        echo -e "${BLUE}=== Bilan $scenario / $OS : ${GREEN}$pass OK${NC}, ${RED}$fail KO${NC} ${BLUE}===${NC}"
        awk -F'\t' '$1=="FAIL"{printf "  ✗ %s — %s\n", $2, $3}' "$out/results.tsv"
        [ "$fail" -eq 0 ] || rc=1
    else
        warn "Aucun résultat : le scénario s'est arrêté avant les contrôles"
        rc=1
    fi

    if [ "$KEEP" = true ]; then
        info "VM gardée en l'état : ./bench.sh shell --os $OS   (IP : $(multipass info "$vm" --format csv | awk -F, 'NR==2{print $3}'))"
    else
        multipass stop --force "$vm"
    fi
    info "Résultats : $out"
    return "$rc"
}

# --- Parsing ---
[ $# -ge 1 ] || usage
CMD="$1"; shift
SCENARIO=""
if [ "$CMD" = "run" ]; then
    [ $# -ge 1 ] || die "Scénario manquant"
    SCENARIO="$1"; shift
fi
while [ $# -gt 0 ]; do
    case "$1" in
        --os)          OS="$2"; shift 2 ;;
        --deb)         DEB="$(realpath "$2")"; shift 2 ;;
        --keep)        KEEP=true; shift ;;
        --no-degraded) DEGRADED=false; shift ;;
        --no-prepull)  PREPULL=false; shift ;;
        --rebuild)     REBUILD=true; shift ;;
        --all)         ALL=true; shift ;;
        -h|--help)     usage ;;
        *) die "Option inconnue : $1" ;;
    esac
done
image_for_os "$OS" >/dev/null
command -v multipass >/dev/null || die "Multipass absent : sudo snap install multipass"

case "$CMD" in
    list)  list_scenarios ;;
    base)  build_base ;;
    run)   run_scenario "$SCENARIO" ;;
    shell) multipass start "ccd-base-$OS" 2>/dev/null; multipass shell "ccd-base-$OS" ;;
    clean)
        # Arrête les VM ; --all les supprime (bases comprises, à reconstruire).
        for vm in $(multipass list --format csv | awk -F, 'NR>1{print $1}' | grep '^ccd-' || true); do
            if [ "$ALL" = true ]; then info "Suppression de $vm"; multipass delete "$vm"
            else multipass stop --force "$vm" 2>/dev/null || true; fi
        done
        [ "$ALL" = true ] && multipass purge ;;
    -h|--help|help) usage ;;
    *) die "Commande inconnue : $CMD" ;;
esac
