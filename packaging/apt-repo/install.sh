#!/bin/bash
# =============================================================================
# Installation de CICADA en une commande
#
#   curl -fsSL https://apt.cicada.reserves-naturelles.org/install.sh | sudo bash
#
# Sur un serveur Debian 12+ ou Ubuntu 22.04+, configure le dépôt de Docker et
# celui de CICADA (avec sa clé de signature), installe le paquet « cicada »,
# puis indique l'adresse du formulaire d'installation. Peut être relancé sans
# risque. Ne modifie rien d'autre sur le serveur.
#
# Options (après « bash -s -- ») :
#   --version X.Y.Z   installer une version précise (défaut : la dernière)
#   --force           continuer sur un système non pris en charge
# =============================================================================
set -euo pipefail

# Adresse du dépôt : surchargée par le banc de test, jamais en usage normal
REPO_URL="${CICADA_APT_URL:-https://apt.cicada.reserves-naturelles.org}"
KEYRING=/usr/share/keyrings/cicada-archive-keyring.gpg
# (pas « VERSION » : /etc/os-release, chargé plus bas, définit cette variable)
CIBLE=""
FORCE=false

while [ $# -gt 0 ]; do
    case "$1" in
        --version) CIBLE="$2"; shift 2 ;;
        --force)   FORCE=true; shift ;;
        -h|--help) echo "Usage : curl -fsSL <dépôt>/install.sh | sudo bash -s -- [--version X.Y.Z] [--force]"; exit 0 ;;
        *) echo "Option inconnue : $1" >&2; exit 1 ;;
    esac
done

etape() { echo; echo "==> $*"; }
echec() { echo "Erreur : $*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || echec "à lancer en root (ajoutez « sudo » devant « bash »)."
[ -r /etc/os-release ] || echec "système non reconnu (pas de /etc/os-release)."
. /etc/os-release

# Systèmes pris en charge (cf. docs/INSTALLATION_GUIDE.md)
pris_en_charge=false
case "${ID:-}" in
    debian) [ "${VERSION_ID%%.*}" -ge 12 ] 2>/dev/null && pris_en_charge=true ;;
    ubuntu) [ "${VERSION_ID%%.*}" -ge 22 ] 2>/dev/null && pris_en_charge=true ;;
esac
if [ "$pris_en_charge" != true ]; then
    msg="${PRETTY_NAME:-ce système} n'est pas pris en charge (Debian 12+ ou Ubuntu 22.04+)."
    [ "$FORCE" = true ] && echo "Attention : $msg Poursuite demandée (--force)." || echec "$msg"
fi
[ "$(dpkg --print-architecture)" = amd64 ] || echec "architecture $(dpkg --print-architecture) non prise en charge (amd64 uniquement)."

export DEBIAN_FRONTEND=noninteractive

etape "Outils de base"
apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg >/dev/null

etape "Dépôt Docker"
if [ -f /etc/apt/sources.list.d/docker.list ] || [ -f /etc/apt/sources.list.d/docker.sources ]; then
    echo "déjà configuré"
else
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL "https://download.docker.com/linux/$ID/gpg" | gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$ID $VERSION_CODENAME stable" \
        > /etc/apt/sources.list.d/docker.list
    echo "configuré pour $ID $VERSION_CODENAME"
fi

etape "Dépôt CICADA ($REPO_URL)"
# Le paquet réinstalle ensuite lui-même cette clé et cette source : elles ne
# servent ici qu'à pouvoir l'installer la première fois.
curl -fsSL "$REPO_URL/cicada-repo-key.gpg" | gpg --dearmor --yes -o "$KEYRING"
chmod a+r "$KEYRING"
echo "deb [signed-by=$KEYRING] $REPO_URL stable main" > /etc/apt/sources.list.d/cicada.list
apt-get update -qq

etape "Installation du paquet cicada${CIBLE:+ $CIBLE} (Docker compris, quelques minutes)"
apt-get install -y "cicada${CIBLE:+=$CIBLE}"

# Adresse à ouvrir : celle par laquelle ce serveur sort sur le réseau
ip_serveur="$(ip -4 route get 1.1.1.1 2>/dev/null | sed -n 's/.* src \([0-9.]*\).*/\1/p')"
[ -n "$ip_serveur" ] || ip_serveur="$(hostname -I 2>/dev/null | awk '{print $1}')"

# Le formulaire démarre avec le paquet : lui laisser quelques secondes
for _ in $(seq 15); do
    curl -sf --max-time 5 http://127.0.0.1:4567/api/health >/dev/null 2>&1 && break
    [ -f /var/lib/cicada/.env ] && break
    sleep 2
done

echo
if curl -sf --max-time 10 http://127.0.0.1:4567/api/health >/dev/null 2>&1; then
    echo "============================================================"
    echo " CICADA $(dpkg-query -W -f '${Version}' cicada) est installé."
    echo " Poursuivez dans votre navigateur :"
    echo "   http://${ip_serveur:-<adresse-du-serveur>}:4567"
    echo "============================================================"
elif [ -f /var/lib/cicada/.env ]; then
    echo "CICADA $(dpkg-query -W -f '${Version}' cicada) est installé ; cette instance était déjà configurée."
else
    echo "Le paquet est installé, mais le formulaire d'installation ne répond pas encore."
    echo "Vérifiez : sudo systemctl status cicada-installer"
    exit 1
fi
