#!/bin/bash
set -e

# Déterminer le répertoire du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration (VERSION doit correspondre au tag des images sur ghcr.io/rnf-si/cicada-*)
PACKAGE_NAME="cicada"
VERSION="${VERSION:-0.1.15}"
ARCH="amd64"
DEB_DIR="$SCRIPT_DIR/debian"
BUILD_DIR="$SCRIPT_DIR/build"

# URL de l'API de suivi (à définir avant de construire le package)
TRACKING_API_URL="${TRACKING_API_URL:-https://tracking.cicada.reserves-naturelles.org/api}"

echo "Construction du package ${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
echo "URL de l'API de suivi : ${TRACKING_API_URL}"

# Vérifier que le répertoire debian existe
if [ ! -d "$DEB_DIR" ]; then
    echo "Erreur : Le répertoire $DEB_DIR n'existe pas"
    exit 1
fi

# Créer le répertoire de build
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Copier la structure du package
cp -r "$DEB_DIR" "$BUILD_DIR/${PACKAGE_NAME}"

# Copier uniquement docker/ (init SQL, etc.) - les images sont pré-buildées sur GHCR
if [ -d "$PROJECT_ROOT/docker" ]; then
    mkdir -p "$BUILD_DIR/${PACKAGE_NAME}/usr/share/cicada"
    cp -r "$PROJECT_ROOT/docker" "$BUILD_DIR/${PACKAGE_NAME}/usr/share/cicada/"
fi

# Injecter l'URL de l'API de suivi et la version dans cicada.conf
# S'assurer que l'URL a le schéma https://
TRACKING_API_URL_FIXED="${TRACKING_API_URL}"
if [[ ! "$TRACKING_API_URL_FIXED" =~ ^https?:// ]]; then
    TRACKING_API_URL_FIXED="https://${TRACKING_API_URL_FIXED}"
fi
sed -i "s|TRACKING_API_URL=.*|TRACKING_API_URL=${TRACKING_API_URL_FIXED}|" \
    "$BUILD_DIR/${PACKAGE_NAME}/etc/cicada/cicada.conf"
sed -i "s|^VERSION=.*|VERSION=${VERSION}|" \
    "$BUILD_DIR/${PACKAGE_NAME}/etc/cicada/cicada.conf"

# Mettre à jour la version dans control
sed -i "s/Version: .*/Version: ${VERSION}/" \
    "$BUILD_DIR/${PACKAGE_NAME}/DEBIAN/control"

# Construire le package
dpkg-deb --build "$BUILD_DIR/${PACKAGE_NAME}" \
    "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

echo "Package créé : $BUILD_DIR/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
