#!/bin/bash
set -e

# Déterminer le répertoire du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Configuration (VERSION doit correspondre au tag des images sur ghcr.io/rnf-si/cicada-*)
PACKAGE_NAME="cicada"
# Version : depuis env var, ou depuis version.txt à la racine du projet
VERSION="${VERSION:-$(cat "$PROJECT_ROOT/version.txt" 2>/dev/null | tr -d '[:space:]' || echo "0.0.0")}"
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

# Version du paquet : fichier du paquet, JAMAIS dans cicada.conf. Celui-ci est
# un conffile : dès qu'un administrateur l'a modifié, dpkg pose une question à
# chaque mise à jour (bloquante en non-interactif), et s'il garde son fichier
# l'ancienne version restait lue — paquet à jour, conteneurs pas redéployés.
echo "$VERSION" > "$BUILD_DIR/${PACKAGE_NAME}/usr/share/cicada/VERSION"

# Injecter l'URL de l'API de suivi dans cicada.conf
# S'assurer que l'URL a le schéma https://
TRACKING_API_URL_FIXED="${TRACKING_API_URL}"
if [[ ! "$TRACKING_API_URL_FIXED" =~ ^https?:// ]]; then
    TRACKING_API_URL_FIXED="https://${TRACKING_API_URL_FIXED}"
fi
sed -i "s|TRACKING_API_URL=.*|TRACKING_API_URL=${TRACKING_API_URL_FIXED}|" \
    "$BUILD_DIR/${PACKAGE_NAME}/etc/cicada/cicada.conf"

# Mettre à jour la version dans control
sed -i "s/Version: .*/Version: ${VERSION}/" \
    "$BUILD_DIR/${PACKAGE_NAME}/DEBIAN/control"

# Permissions indépendantes de l'umask de la machine de construction
# (sinon fichiers installés modifiables par le groupe)
chmod -R go-w "$BUILD_DIR/${PACKAGE_NAME}"

# Ne pas embarquer le bytecode Python laissé par un lancement local de l'installateur
find "$BUILD_DIR/${PACKAGE_NAME}" -name __pycache__ -type d -prune -exec rm -rf {} +

# Construire le package
# -Zxz : sur Ubuntu (poste de dev comme runner CI), dpkg-deb compresse en zstd
# par défaut, format que le dpkg de Debian 11 ne sait pas lire (#221). xz est lu
# partout. --root-owner-group : fichiers à root dans le paquet, quel que soit
# l'utilisateur qui construit.
dpkg-deb -Zxz --root-owner-group --build "$BUILD_DIR/${PACKAGE_NAME}" \
    "$BUILD_DIR/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"

echo "Package créé : $BUILD_DIR/${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
