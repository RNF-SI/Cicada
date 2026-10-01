#!/bin/bash
# =============================================================================
# Labo CICADA persistant : l'infrastructure RNF complète en local, sur la durée
#
# 4 VM laissées allumées : CICADA (installé depuis le dépôt), serveur de bases,
# hub d'exploration, serveur de suivi + dépôt APT. Le heartbeat
# part réellement chaque nuit ; les releases se simulent à la demande.
#
#   ./labo.sh demarrer [--version 0.1.47]  # installe tout (≈ 15 min), repart de zéro
#   ./labo.sh statut                       # versions, dernier heartbeat, hub…
#   ./labo.sh publier 0.1.49               # release : dépôt APT + version annoncée
#   ./labo.sh heartbeat                    # heartbeat tout de suite (sans attendre 03:00)
#   ./labo.sh hub                          # publication vers le hub (sinon chaque nuit, 2h30)
#   ./labo.sh acces                        # rappeler adresses et identifiants
#   ./labo.sh pause | reprendre            # éteindre / rallumer les 4 VM (état conservé)
#   ./labo.sh fin                          # éteindre et oublier le labo
#
# Une release n'est complète que si les images Docker de la version existent sur
# GHCR : seules les versions publiées (taguées) peuvent être « publiées » ici.
# =============================================================================
set -euo pipefail

BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGING_DIR="$(cd "$BENCH_DIR/.." && pwd)"
OS="debian12"
STATE="$BENCH_DIR/results/labo.env"
GUEST_DIR=/home/ubuntu/bench
VMS=(ccd-base-$OS ccd-db-$OS ccd-hub-$OS ccd-tracking-$OS)
CICADA="ccd-base-$OS"; TRACKING="ccd-tracking-$OS"; HUB="ccd-hub-$OS"

GREEN='\033[0;32m'; BLUE='\033[0;34m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info() { echo -e "${BLUE}[labo]${NC} $*"; }
die()  { echo -e "${RED}[labo] $*${NC}" >&2; exit 1; }
vx()   { local vm="$1"; shift; multipass exec "$vm" -- sudo "$@"; }
vm_ip() { multipass info "$1" --format csv | awk -F, 'NR==2{print $3}'; }
usage() { sed -n '2,/^# =====/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'; exit 0; }
need_state() { [ -f "$STATE" ] || die "Pas de labo : ./labo.sh demarrer"; . "$STATE"; }

save_state() {
    local cicada_ip tracking_ip hub_ip jetons
    cicada_ip="$(vm_ip "$CICADA")"; tracking_ip="$(vm_ip "$TRACKING")"; hub_ip="$(vm_ip "$HUB")"
    jetons="$(ls -td "$BENCH_DIR"/results/*-labo-"$OS"/hub-jetons 2>/dev/null | head -1)"
    {
        echo "CICADA_IP=$cicada_ip"
        echo "TRACKING_IP=$tracking_ip"
        echo "HUB_IP=$hub_ip"
        echo "DB_IP=$(vm_ip "ccd-db-$OS")"
        [ -n "$jetons" ] && sed 's/^/LABO_/' "$jetons"
    } > "$STATE"
}

acces() {
    need_state
    cat <<EOF

$(echo -e "${GREEN}=== Labo CICADA ===${NC}")

  Application          http://$CICADA_IP:8080
                       admin@bench.test / Bench-Test-123!   (super-admin)
  Serveur de suivi     http://$TRACKING_IP/admin/
                       admin / Bench-Tracking-1             (instances, versions, heartbeats)
  Dépôt APT            apt.cicada.bench (sur $TRACKING_IP) — contenu : ./labo.sh statut
  Hub d'exploration    ${LABO_HUB_URL:-http://$HUB_IP}   (API seule)
  Serveur de bases     $DB_IP (PostgreSQL 17 + PostGIS, base « geonature » voisine)

  Entrer dans une VM   multipass shell $CICADA | ccd-db-$OS | $HUB | $TRACKING
  Journaux CICADA      sudo docker logs -f cicada_prod_web   (dans $CICADA)
  Updater / heartbeat  sudo tail -f /var/log/cicada/updater.log /var/log/cicada/heartbeat.log

EOF
}

demarrer() {
    local version="0.1.47"
    [ "${1:-}" = "--version" ] && version="$2"
    info "Installation du labo (CICADA $version depuis le dépôt) — environ 15 minutes"
    # bench.sh restaure les 4 VM à leur état initial puis déroule le scénario « labo »
    TRACKING_FROM_VERSION="$version" "$BENCH_DIR/bench.sh" run labo --keep --os "$OS" \
        || echo -e "${YELLOW}[labo] Des contrôles ont échoué : voir le bilan ci-dessus${NC}"
    save_state
    # Rien n'est encore publié : le serveur de suivi annonce la version installée
    # (les tests automatiques, eux, annoncent d'emblée la version cible).
    vx "$TRACKING" bash -c "sed -i 's/^LATEST_VERSION=.*/LATEST_VERSION=$version/' /opt/tracking-api/.env && systemctl restart cicada-tracking-api"
    vx "$CICADA" systemctl start cicada-heartbeat.service || true
    acces
    echo "  Ensuite : ./labo.sh publier <version>  puis bouton « Mettre à jour » dans l'administration."
}

statut() {
    need_state
    echo -e "${BLUE}Machines${NC}"
    multipass list | grep -E "Name|$OS" | grep -E "Name|base|db|hub|tracking"
    echo -e "\n${BLUE}CICADA${NC} ($CICADA_IP)"
    vx "$CICADA" bash -c '
        echo "  paquet    : $(dpkg-query -W -f "\${Version}" cicada 2>/dev/null)"
        echo "  images    : $(docker ps --format "{{.Image}}" | grep cicada-backend | sort -u | tr "\n" " ")"
        echo "  web       : $(docker inspect -f "{{.State.Health.Status}}" cicada_prod_web 2>/dev/null)"
        echo "  annoncé   : $(cat /var/lib/cicada/updates/update_available.json 2>/dev/null)"
        echo "  heartbeat : prochain $(systemctl show cicada-heartbeat.timer -p NextElapseUSecRealtime --value)"
        [ -f /var/lib/cicada/updates/update_result.json ] && echo "  dernière mise à jour : $(cat /var/lib/cicada/updates/update_result.json)"
        true'
    echo -e "\n${BLUE}Serveur de suivi${NC} ($TRACKING_IP)"
    vx "$TRACKING" bash -s <<'EOS'
echo "  version annoncée : $(grep ^LATEST_VERSION= /opt/tracking-api/.env | cut -d= -f2)"
echo "  dépôt APT        : $(reprepro -b /var/www/repos/cicada list stable 2>/dev/null)"
echo "  instances connues (version | dernier heartbeat) :"
runuser -u postgres -- psql -d tracking -At -F ' | ' -c \
    "select version, coalesce(to_char(last_heartbeat, 'YYYY-MM-DD HH24:MI'), 'jamais') from tracking_instances" \
    | sed 's/^/    /'
EOS
    echo -e "\n${BLUE}Hub${NC} (${LABO_HUB_URL:-?})"
    if [ -n "${LABO_HUB_READ:-}" ]; then
        curl -s --max-time 10 -H "X-Hub-Token: $LABO_HUB_READ" "$LABO_HUB_URL/api/federation/instances/" \
            | python3 -c "$(cat <<'PY'
import json, sys
for r in json.load(sys.stdin).get('instances', []):
    print('  {} : {} plan(s) publié(s), dernière publication {}'.format(
        r['instance_id'], r.get('plans_publies', 0), r.get('derniere_publication') or 'aucune'))
PY
)" \
            2>/dev/null || echo "  injoignable"
    fi
}

publier() {
    local version="${1:-}"
    [[ "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "Usage : ./labo.sh publier X.Y.Z"
    need_state
    if ! docker manifest inspect "ghcr.io/rnf-si/cicada-backend:$version" >/dev/null 2>&1; then
        die "Pas d'image ghcr.io/rnf-si/cicada-backend:$version : la mise à jour échouerait au téléchargement des images. Seules les versions publiées (taguées) sont utilisables."
    fi
    info "Construction du paquet $version (URL de suivi du labo)"
    (cd "$PACKAGING_DIR" && VERSION="$version" TRACKING_API_URL="http://tracking.cicada.bench/api" ./build-deb.sh >/dev/null)
    multipass transfer "$PACKAGING_DIR/build/cicada_${version}_amd64.deb" "$TRACKING:$GUEST_DIR/"
    info "Publication dans le dépôt APT"
    vx "$TRACKING" env GNUPGHOME=/root/.gnupg bash "$GUEST_DIR/apt-repo/publish.sh" \
        "$GUEST_DIR/cicada_${version}_amd64.deb" --dir /var/www/repos/cicada
    info "Version annoncée par le serveur de suivi : $version"
    vx "$TRACKING" bash -c "sed -i 's/^LATEST_VERSION=.*/LATEST_VERSION=$version/' /opt/tracking-api/.env && systemctl restart cicada-tracking-api"
    echo
    echo "  Le heartbeat de cette nuit l'annoncera à l'instance ; pour ne pas attendre :"
    echo "    ./labo.sh heartbeat"
    echo "  puis, dans l'application (super-admin) : bouton « Mettre à jour »."
}

heartbeat() {
    need_state
    vx "$CICADA" systemctl start cicada-heartbeat.service
    vx "$CICADA" tail -3 /var/log/cicada/heartbeat.log
    echo "  Annoncé à l'application : $(vx "$CICADA" cat /var/lib/cicada/updates/update_available.json)"
}

hub() {
    need_state
    info "Publication vers le hub (celle que la tâche planifiée fait chaque nuit à 2h30)"
    vx "$CICADA" docker exec cicada_prod_web python manage.py push_federation \
        || echo -e "${YELLOW}  Rappels : la version installée doit savoir publier (≥ 0.1.48), et le partage
  doit être activé par un super-admin dans Administration → Paramètres.${NC}"
}

[ $# -ge 1 ] || usage
cmd="$1"; shift
case "$cmd" in
    demarrer)  demarrer "$@" ;;
    statut)    statut ;;
    publier)   publier "$@" ;;
    heartbeat) heartbeat ;;
    hub)       hub ;;
    acces)     acces ;;
    pause)     for v in "${VMS[@]}"; do multipass stop "$v" 2>/dev/null || true; done; info "Labo en pause (état conservé) : ./labo.sh reprendre" ;;
    reprendre) for v in "${VMS[@]}"; do multipass start "$v"; done; save_state; acces ;;
    fin)       for v in "${VMS[@]}"; do multipass stop --force "$v" 2>/dev/null || true; done; rm -f "$STATE"; info "Labo arrêté" ;;
    -h|--help|help) usage ;;
    *) die "Commande inconnue : $cmd (./labo.sh --help)" ;;
esac
