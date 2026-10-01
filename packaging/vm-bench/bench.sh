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
#   ./bench.sh base [--os debian12] [--role cicada|db|hub|tracking] [--rebuild]
#                                           # (re)construire une VM de base
#   ./bench.sh shell [--os …]               # shell dans la VM (état du dernier run)
#   ./bench.sh clean [--all]                # arrêter les VM (--all : les supprimer)
#
# Labo persistant (infrastructure complète laissée allumée) : voir ./labo.sh
#
# Options de run :
#   --os debian12|debian13|ubuntu24   système cible (défaut : debian12)
#   --deb CHEMIN      .deb à tester (défaut : construit depuis l'arbre courant)
#   --from-deb CHEMIN .deb installé AVANT le paquet testé (scénario upgrade)
#   --keep            laisser la VM allumée après le run (pour inspecter)
#   --manuel          s'arrêter avant le formulaire : vous le remplissez dans
#                     votre navigateur (implique --keep)
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
FROM_DEB=""
KEEP=false
DEGRADED=true
MANUAL=false
PREPULL=true
REBUILD=false
ALL=false
ROLE="cicada"

# Identité de l'instance testée auprès du hub (scénarios avec hub)
HUB_INSTANCE_ID="bench"
HUB_INSTANCE_LABEL="Instance du banc"
# Version initiale des scénarios « tracking » (images publiées sur GHCR)
TRACKING_FROM_VERSION="${TRACKING_FROM_VERSION:-0.1.47}"

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
                # Reprise (-C -) : le miroir coupe parfois en cours de route
                local try
                for try in 1 2 3; do
                    curl -fsSL --retry 5 --retry-delay 3 -C - -o "$file.part" "$src" >&2 && break
                    warn "Téléchargement interrompu, reprise ($try/3)" >&2
                done
                # Somme publiée à côté de l'image : une image tronquée ferait
                # échouer multipass bien plus loin, sans message clair.
                local expected actual
                expected="$(curl -fsSL "$(dirname "$src")/SHA512SUMS" | awk -v f="$(basename "$src")" '$2==f{print $1}')"
                actual="$(sha512sum "$file.part" | awk '{print $1}')"
                if [ -z "$expected" ] || [ "$expected" != "$actual" ]; then
                    rm -f "$file.part"
                    die "Image $(basename "$src") corrompue ou somme SHA512 introuvable : relancer"
                fi
                mv "$file.part" "$file"
            fi
            echo "file://$file" ;;
        *) echo "$src" ;;
    esac
}

vm_ip() { multipass info "$1" --format csv | awk -F, 'NR==2{print $3}'; }

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
    local source; source="$(launch_source)" || exit 2
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

# --- VM « serveur de base » (scénarios marqués « # DB_VM: oui ») ---
# PostgreSQL + PostGIS sur une autre machine que CICADA, joignable par le
# réseau : topologie RNF (bases dans un conteneur/VM dédiés). Même principe de
# socle que la VM CICADA.
build_db_base() {
    local dbvm="ccd-db-$OS"
    if vm_exists "$dbvm"; then
        [ "$REBUILD" = true ] || return 0
        multipass delete --purge "$dbvm"
    fi
    local source; source="$(launch_source)" || exit 2
    info "Création de la VM serveur de base $dbvm"
    multipass launch "$source" --name "$dbvm" --cpus 2 --memory 2G --disk 10G --timeout 900
    push_guest_scripts "$dbvm"
    vx "$dbvm" bash "$GUEST_DIR/guest/db-server-setup.sh"
    multipass stop "$dbvm"
    multipass snapshot "$dbvm" --name socle >/dev/null
    info "Serveur de base $dbvm prêt (instantané « socle »)"
}

# --- VM « hub » (scénarios marqués « # HUB_VM: oui ») ---
# Déployée comme le décrit docs/DEPLOIEMENT_HUB.md : image GHCR, compose de
# production, Apache devant, enroler_instance.
build_hub_base() {
    local hubvm="ccd-hub-$OS" version
    version="$(tr -d '[:space:]' < "$PROJECT_ROOT/version.txt")"
    if vm_exists "$hubvm"; then
        [ "$REBUILD" = true ] || return 0
        multipass delete --purge "$hubvm"
    fi
    local source; source="$(launch_source)" || exit 2
    info "Création de la VM hub $hubvm"
    multipass launch "$source" --name "$hubvm" --cpus 2 --memory 3G --disk 15G --timeout 900
    push_guest_scripts "$hubvm"
    # Fichiers de déploiement du dépôt (le guide fait un git clone dans /opt/cicada-hub)
    vx "$hubvm" mkdir -p /opt/cicada-hub/hub/docker/postgres
    multipass transfer "$PROJECT_ROOT/docker-compose.hub.prod.yml" "$hubvm:/home/ubuntu/docker-compose.hub.prod.yml"
    multipass transfer "$PROJECT_ROOT/.env.hub.prod.example" "$hubvm:/home/ubuntu/.env.hub.prod.example"
    multipass transfer "$PROJECT_ROOT/hub/docker/postgres/init.sql" "$hubvm:/home/ubuntu/hub-init.sql"
    vx "$hubvm" bash -c 'mv /home/ubuntu/docker-compose.hub.prod.yml /home/ubuntu/.env.hub.prod.example /opt/cicada-hub/ && mv /home/ubuntu/hub-init.sql /opt/cicada-hub/hub/docker/postgres/init.sql'
    vx "$hubvm" bash "$GUEST_DIR/guest/hub-server-setup.sh" "$version"
    multipass stop "$hubvm"
    multipass snapshot "$hubvm" --name socle >/dev/null
    info "Hub $hubvm prêt (instantané « socle »)"
}

# --- VM « tracking » (scénarios marqués « # TRACKING_VM: oui ») ---
# Le serveur TrackingCicada : API de suivi (tracking-api/) + dépôt APT signé.
build_tracking_base() {
    local tvm="ccd-tracking-$OS"
    if vm_exists "$tvm"; then
        [ "$REBUILD" = true ] || return 0
        multipass delete --purge "$tvm"
    fi
    local source; source="$(launch_source)" || exit 2
    info "Création de la VM tracking $tvm"
    multipass launch "$source" --name "$tvm" --cpus 2 --memory 2G --disk 10G --timeout 900
    push_guest_scripts "$tvm"
    vx "$tvm" bash "$GUEST_DIR/guest/tracking-server-setup.sh"
    multipass stop "$tvm"
    multipass snapshot "$tvm" --name socle >/dev/null
    info "Tracking $tvm prêt (instantané « socle »)"
}

# Paquets d'un scénario « tracking » : construits depuis l'arbre courant avec
# l'URL de suivi du banc gravée dedans (comme la CI grave celle de prod), en
# deux versions dont les images existent sur GHCR : l'initiale et la cible.
build_tracking_debs() {
    local url="http://tracking.cicada.bench/api" v
    mkdir -p "$BENCH_DIR/results"
    for v in "$TRACKING_FROM_VERSION" "$(tr -d '[:space:]' < "$PROJECT_ROOT/version.txt")"; do
        (cd "$PACKAGING_DIR" && VERSION="$v" TRACKING_API_URL="$url" ./build-deb.sh >/dev/null)
        cp "$PACKAGING_DIR/build/cicada_${v}_amd64.deb" "$BENCH_DIR/results/tracking-cicada_${v}_amd64.deb"
    done
}

restore_vm() {
    local vm="$1"
    [ "$(vm_state "$vm")" = Stopped ] || multipass stop --force "$vm"
    multipass restore --destructive "$vm.socle" >/dev/null
    multipass start "$vm"
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
    restore_vm "$vm"

    local dbvm="" db_ip=""
    if grep -q '^# DB_VM: oui' "$scenario_file"; then
        dbvm="ccd-db-$OS"
        build_db_base
        info "Restauration du serveur de base $dbvm"
        restore_vm "$dbvm"
        db_ip="$(vm_ip "$dbvm")"
        push_guest_scripts "$dbvm"
    fi

    push_guest_scripts "$vm"
    multipass transfer "$DEB" "$vm:$GUEST_DIR/cicada.deb"
    if [ -n "$FROM_DEB" ]; then
        multipass transfer "$FROM_DEB" "$vm:$GUEST_DIR/cicada-initial.deb"
    fi

    local tvm="" tracking_ip=""
    if grep -q '^# TRACKING_VM: oui' "$scenario_file"; then
        tvm="ccd-tracking-$OS"
        local target; target="$(tr -d '[:space:]' < "$PROJECT_ROOT/version.txt")"
        build_tracking_debs
        build_tracking_base
        info "Restauration et déploiement du serveur de suivi $tvm"
        restore_vm "$tvm"
        push_guest_scripts "$tvm"
        multipass transfer -r "$PROJECT_ROOT/tracking-api" "$tvm:$GUEST_DIR/"
        multipass transfer -r "$PACKAGING_DIR/apt-repo" "$tvm:$GUEST_DIR/"
        vx "$tvm" find "$GUEST_DIR/tracking-api" -name __pycache__ -prune -exec rm -rf {} +
        multipass transfer "$BENCH_DIR/results/tracking-cicada_${TRACKING_FROM_VERSION}_amd64.deb" "$tvm:$GUEST_DIR/"
        multipass transfer "$BENCH_DIR/results/tracking-cicada_${target}_amd64.deb" "$tvm:$GUEST_DIR/"
        set +e
        vx "$tvm" env BENCH_DIR="$GUEST_DIR" bash "$GUEST_DIR/guest/tracking-side.sh" "$target" \
            "$GUEST_DIR/tracking-cicada_${TRACKING_FROM_VERSION}_amd64.deb" > "$out/tracking-server.log" 2>&1
        set -e
        sed 's/^/   [tracking] /' "$out/tracking-server.log"
        multipass transfer "$tvm:$GUEST_DIR/results.tsv" "$out/tracking-results.tsv" 2>/dev/null || true
        tracking_ip="$(vm_ip "$tvm")"
        # La VM CICADA installe la version initiale depuis le dépôt ; cicada.deb
        # (la cible) ne sert qu'aux contrôles statiques du paquet.
        DEB="$BENCH_DIR/results/tracking-cicada_${target}_amd64.deb"
        multipass transfer "$DEB" "$vm:$GUEST_DIR/cicada.deb"
    fi

    local hubvm="" hub_env=()
    if grep -q '^# HUB_VM: oui' "$scenario_file"; then
        hubvm="ccd-hub-$OS"
        build_hub_base
        info "Restauration et déploiement du hub $hubvm"
        restore_vm "$hubvm"
        push_guest_scripts "$hubvm"
        set +e
        vx "$hubvm" env BENCH_DIR="$GUEST_DIR" bash "$GUEST_DIR/guest/hub-side.sh" \
            "$(tr -d '[:space:]' < "$PROJECT_ROOT/version.txt")" "$HUB_INSTANCE_ID" "$HUB_INSTANCE_LABEL" \
            "http://$(vm_ip "$vm"):8080" > "$out/hub-server.log" 2>&1
        set -e
        sed 's/^/   [hub] /' "$out/hub-server.log"
        multipass transfer "$hubvm:$GUEST_DIR/results.tsv" "$out/hub-results.tsv" 2>/dev/null || true
        multipass transfer "$hubvm:$GUEST_DIR/hub-jetons" "$out/hub-jetons" 2>/dev/null || true
        if [ -f "$out/hub-jetons" ]; then
            hub_env=(BENCH_HUB_URL="$(awk -F= '/^HUB_URL=/{print $2}' "$out/hub-jetons")"
                     BENCH_HUB_PUSH="$(awk -F= '/^HUB_PUSH=/{print $2}' "$out/hub-jetons")"
                     BENCH_HUB_READ="$(awk -F= '/^HUB_READ=/{print $2}' "$out/hub-jetons")")
        fi
    fi

    info "Scénario $scenario sur $OS — journal : $out/run.log"
    local rc
    set +e
    multipass exec "$vm" -- sudo env \
        BENCH_DEGRADED="$DEGRADED" BENCH_OS="$OS" BENCH_DIR="$GUEST_DIR" BENCH_DB_HOST="$db_ip" BENCH_MANUAL="$MANUAL" \
        BENCH_HUB_INSTANCE_ID="$HUB_INSTANCE_ID" BENCH_HUB_INSTANCE_LABEL="$HUB_INSTANCE_LABEL" "${hub_env[@]}" \
        BENCH_TRACKING_IP="$tracking_ip" BENCH_TRACKING_FROM="$TRACKING_FROM_VERSION" \
        bash "$GUEST_DIR/guest/run-scenario.sh" "$scenario" > >(tee "$out/run.log") 2>&1 &
    local main_pid=$!
    # Rendez-vous entre la VM CICADA et les autres, tant que le scénario tourne :
    #  - attente-base : son installateur tourne ; le serveur de base se prépare
    #    comme le ferait son administrateur, le résultat revient dans base-prete ;
    #  - rdv-publier : la nouvelle version est publiée dans le dépôt APT
    #    (comme à une release), rdv-publier.ok signale que c'est fait.
    local base_faite=false publie=false
    while [ "$MANUAL" != true ] && { [ -n "$dbvm" ] || [ -n "$tvm" ]; } && kill -0 "$main_pid" 2>/dev/null; do
        if [ -n "$tvm" ] && [ "$publie" = false ] && vx "$vm" test -f "$GUEST_DIR/rdv-publier" 2>/dev/null; then
            vx "$tvm" env GNUPGHOME=/root/.gnupg bash "$GUEST_DIR/apt-repo/publish.sh" \
                "$GUEST_DIR/tracking-cicada_${target}_amd64.deb" --dir /var/www/repos/cicada \
                > "$out/tracking-publish.log" 2>&1
            sed 's/^/   [tracking] /' "$out/tracking-publish.log"
            vx "$vm" touch "$GUEST_DIR/rdv-publier.ok"
            publie=true
        fi
        if [ -n "$dbvm" ] && [ "$base_faite" = false ] && vx "$vm" test -f "$GUEST_DIR/attente-base" 2>/dev/null; then
            base_faite=true
            vx "$dbvm" env BENCH_DIR="$GUEST_DIR" bash "$GUEST_DIR/guest/db-side.sh" "$scenario" "$(vm_ip "$vm")" \
                > "$out/db-server.log" 2>&1
            sed 's/^/   [serveur de base] /' "$out/db-server.log"
            multipass transfer "$dbvm:$GUEST_DIR/results.tsv" "$out/db-results.tsv" 2>/dev/null || true
            multipass transfer "$dbvm:$GUEST_DIR/base-prete" "$out/base-prete" 2>/dev/null || touch "$out/base-prete"
            multipass transfer "$out/base-prete" "$vm:$GUEST_DIR/base-prete"
        fi
        sleep 3
    done
    wait "$main_pid"
    rc=$?
    set -e

    # Artefacts utiles au diagnostic, même en cas d'échec
    multipass transfer "$vm:$GUEST_DIR/results.tsv" "$out/results.tsv" 2>/dev/null || true
    vx "$vm" bash "$GUEST_DIR/guest/collect.sh" > "$out/diagnostic.txt" 2>&1 || true
    if [ -n "$dbvm" ]; then
        # Contrôles faits côté serveur de base, en tête du bilan
        [ -f "$out/db-results.tsv" ] && cat "$out/db-results.tsv" "$out/results.tsv" > "$out/all.tsv" \
            && mv "$out/all.tsv" "$out/results.tsv"
        vx "$dbvm" bash -c 'tail -40 /var/log/postgresql/postgresql-*-main.log' > "$out/db-server-pg.log" 2>&1 || true
        [ "$KEEP" = true ] || multipass stop --force "$dbvm"
    fi
    if [ -n "$tvm" ]; then
        [ -f "$out/tracking-results.tsv" ] && cat "$out/tracking-results.tsv" "$out/results.tsv" > "$out/all.tsv" \
            && mv "$out/all.tsv" "$out/results.tsv"
        vx "$tvm" bash -c 'journalctl -u cicada-tracking-api --no-pager | tail -40; runuser -u postgres -- psql -d tracking -c "select token, version, last_heartbeat from tracking_instances"' \
            > "$out/tracking-diag.txt" 2>&1 || true
        [ "$KEEP" = true ] || multipass stop --force "$tvm"
    fi
    if [ -n "$hubvm" ]; then
        local merged="$out/results.tsv"
        [ -f "$out/hub-results.tsv" ] && cat "$out/hub-results.tsv" "$merged" > "$out/all.tsv" && mv "$out/all.tsv" "$merged"
        vx "$hubvm" bash -c 'cd /opt/cicada-hub && docker compose -f docker-compose.hub.prod.yml --env-file .env.hub.prod logs --tail 60 hub' \
            > "$out/hub-logs.txt" 2>&1 || true
        [ "$KEEP" = true ] || multipass stop --force "$hubvm"
    fi

    if [ "$MANUAL" = true ]; then
        manual_instructions "$vm" "$dbvm" "$db_ip" "$out/hub-jetons"
        return 0
    fi

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

manual_instructions() {
    local vm="$1" dbvm="$2" db_ip="$3" jetons="${4:-}" ip
    ip="$(vm_ip "$vm")"
    echo
    echo -e "${GREEN}=== Prêt : remplissez le formulaire vous-même ===${NC}"
    echo
    echo "  Formulaire        : http://$ip:4567"
    echo "  Après installation: http://$ip:8080   (domaine à saisir : $ip)"
    if [ -n "$dbvm" ]; then
        echo
        echo "  Base de données   : choisir « Serveur PostgreSQL existant », hôte $db_ip"
        echo "  Serveur de base   : multipass shell $dbvm"
        echo "                      puis y lancer la commande affichée par le formulaire"
        echo "  (une base « geonature » y existe déjà, comme sur un serveur mutualisé)"
    fi
    if [ -n "$jetons" ] && [ -f "$jetons" ]; then
        echo
        echo "  Exploration fédérée (section du formulaire) :"
        echo "    Identifiant d'instance : $HUB_INSTANCE_ID     Nom : $HUB_INSTANCE_LABEL"
        echo "    URL du hub             : $(awk -F= '/^HUB_URL=/{print $2}' "$jetons")"
        echo "    Jeton de dépôt         : $(awk -F= '/^HUB_PUSH=/{print $2}' "$jetons")"
        echo "    Jeton de lecture       : $(awk -F= '/^HUB_READ=/{print $2}' "$jetons")"
        echo "  Hub                   : multipass shell ccd-hub-$OS   (cd /opt/cicada-hub)"
    fi
    echo
    echo "  Shell CICADA      : multipass shell $vm"
    echo "  Journaux          : sudo docker logs -f cicada_prod_web   (dans la VM)"
    echo "  Fin               : ./bench.sh clean"
    echo
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
        --from-deb)    FROM_DEB="$(realpath "$2")"; shift 2 ;;
        --keep)        KEEP=true; shift ;;
        --manuel)      MANUAL=true; KEEP=true; shift ;;
        --no-degraded) DEGRADED=false; shift ;;
        --no-prepull)  PREPULL=false; shift ;;
        --rebuild)     REBUILD=true; shift ;;
        --all)         ALL=true; shift ;;
        --role)        ROLE="$2"; shift 2 ;;
        -h|--help)     usage ;;
        *) die "Option inconnue : $1" ;;
    esac
done
image_for_os "$OS" >/dev/null
command -v multipass >/dev/null || die "Multipass absent : sudo snap install multipass"

case "$CMD" in
    list)  list_scenarios ;;
    base)
        case "$ROLE" in
            cicada)   build_base ;;
            db)       build_db_base ;;
            hub)      build_hub_base ;;
            tracking) build_tracking_base ;;
            *) die "Rôle inconnu : $ROLE (cicada, db, hub, tracking)" ;;
        esac ;;
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
