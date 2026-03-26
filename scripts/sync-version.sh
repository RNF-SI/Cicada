#!/bin/bash
# =============================================================================
# sync-version.sh — Propage la version depuis version.txt vers tous les fichiers
#
# Source unique : version.txt (racine du projet)
# Fichiers mis à jour :
#   - frontend/package.json
#   - packaging/debian/DEBIAN/control
#   - packaging/debian/etc/cicada/cicada.conf
#
# Les autres fichiers lisent version.txt dynamiquement :
#   - backend/config/version.py (Python, lit au runtime)
#   - packaging/build-deb.sh (shell, lit au build)
#   - packaging/test-*.sh (shell, lit au runtime)
#
# Usage :
#   ./scripts/sync-version.sh           # Propage la version actuelle
#   ./scripts/sync-version.sh 0.2.0     # Change la version ET propage
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION_FILE="$PROJECT_ROOT/version.txt"

# Si une version est passée en argument, mettre à jour version.txt d'abord
if [ -n "$1" ]; then
    echo "$1" > "$VERSION_FILE"
fi

# Lire la version
VERSION="$(cat "$VERSION_FILE" | tr -d '[:space:]')"
if [ -z "$VERSION" ]; then
    echo "Erreur : version.txt est vide"
    exit 1
fi

echo "Synchronisation de la version : $VERSION"

# frontend/package.json
PACKAGE_JSON="$PROJECT_ROOT/frontend/package.json"
if [ -f "$PACKAGE_JSON" ]; then
    # Remplacer la ligne "version": "..." dans package.json
    sed -i "s/\"version\": \"[^\"]*\"/\"version\": \"$VERSION\"/" "$PACKAGE_JSON"
    echo "  ✓ frontend/package.json"
fi

# packaging/debian/DEBIAN/control
CONTROL="$PROJECT_ROOT/packaging/debian/DEBIAN/control"
if [ -f "$CONTROL" ]; then
    sed -i "s/^Version: .*/Version: $VERSION/" "$CONTROL"
    echo "  ✓ packaging/debian/DEBIAN/control"
fi

# packaging/debian/etc/cicada/cicada.conf
CONF="$PROJECT_ROOT/packaging/debian/etc/cicada/cicada.conf"
if [ -f "$CONF" ]; then
    sed -i "s/^VERSION=.*/VERSION=$VERSION/" "$CONF"
    echo "  ✓ packaging/debian/etc/cicada/cicada.conf"
fi

echo ""
echo "Version $VERSION synchronisée dans tous les fichiers."
echo ""
echo "Fichiers qui lisent version.txt dynamiquement (pas de mise à jour nécessaire) :"
echo "  - backend/config/version.py"
echo "  - packaging/build-deb.sh"
echo "  - packaging/test-*.sh"
