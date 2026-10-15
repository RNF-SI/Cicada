#!/bin/bash
# publish.sh — Ajoute un .deb de CICADA au dépôt APT (distribution stable)
#   sudo ./publish.sh cicada_0.1.50_amd64.deb [--dir /var/www/repos/cicada]
# reprepro garde une seule version par paquet et par distribution : publier
# 0.1.50 remplace 0.1.49 (apt install cicada=0.1.49 n'est alors plus possible).
set -euo pipefail
DEB="$1"; shift || true
REPO_DIR="/var/www/repos/cicada"
[ "${1:-}" = "--dir" ] && REPO_DIR="$2"
[ -f "$DEB" ] || { echo "Fichier introuvable : $DEB"; exit 1; }
VERSION="$(dpkg-deb -f "$DEB" Version)"
export GNUPGHOME="${GNUPGHOME:-/root/.gnupg}"
export GPG_TTY="$(tty 2>/dev/null || true)"

# La phrase secrète est demandée ici, en ligne de commande, et gardée par
# l'agent le temps de la publication. Laissée à reprepro, la fenêtre pinentry
# peut ne jamais s'afficher (agent rattaché à un autre terminal, terminal web)
# et expirer : le paquet est alors enregistré mais l'index public n'est pas
# réécrit, et les instances ne voient pas la nouvelle version (constaté 0.1.55).
gpg-connect-agent updatestartuptty /bye >/dev/null 2>&1 || true
CLE="$(awk '/^SignWith:/{print $2; exit}' "$REPO_DIR/conf/distributions")"
echo test | gpg --pinentry-mode loopback ${CLE:+--local-user "$CLE"} --clearsign >/dev/null

# includedeb échoue si l'export (la signature) échoue ; il n'enregistre rien
# de nouveau si la version est déjà là. Dans les deux cas, réécrire l'index.
reprepro -b "$REPO_DIR" includedeb stable "$DEB" || reprepro -b "$REPO_DIR" export stable

# Script d'installation en une commande, servi à la racine du dépôt
ICI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$ICI/install.sh" ] && install -m 0644 "$ICI/install.sh" "$REPO_DIR/install.sh"

# « list » lit la base de reprepro, pas l'index publié : seul ce dernier compte
# pour les instances.
PUBLIE="$(awk '/^Package: cicada$/{p=1} p && /^Version:/{print $2; exit}' \
    "$REPO_DIR/dists/stable/main/binary-amd64/Packages")"
if [ "$PUBLIE" != "$VERSION" ]; then
    echo "ÉCHEC : l'index publié annonce « ${PUBLIE:-rien} », pas $VERSION." >&2
    echo "Relancer : reprepro -b $REPO_DIR export stable" >&2
    exit 1
fi
echo "Publié : cicada $VERSION (index signé le $(date -r "$REPO_DIR/dists/stable/InRelease" '+%d/%m/%Y %H:%M'))"
