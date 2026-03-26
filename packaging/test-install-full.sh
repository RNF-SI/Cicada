#!/bin/bash
set -e

# Script de test complet avec interface web fonctionnelle
# Nécessite Docker-in-Docker ou un environnement plus complet

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

# Version dynamique : cicada.conf > version.txt > env var
VERSION="${VERSION:-$(awk -F= '/^VERSION=/{print $2; exit}' "$SCRIPT_DIR/debian/etc/cicada/cicada.conf" 2>/dev/null || cat "$SCRIPT_DIR/../version.txt" 2>/dev/null || echo "0.0.0")}"
PACKAGE_FILE="$BUILD_DIR/cicada_${VERSION}_amd64.deb"
CONTAINER_NAME="cicada-test-full"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Test complet d'installation CICADA v${VERSION} ===${NC}"

if [ ! -f "$PACKAGE_FILE" ]; then
    echo -e "${RED}Erreur : Le package $PACKAGE_FILE n'existe pas${NC}"
    exit 1
fi

# Nettoyer
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Créer un conteneur avec Docker-in-Docker
echo -e "${YELLOW}Création du conteneur de test avec Docker...${NC}"
docker run -d \
    --name "$CONTAINER_NAME" \
    --privileged \
    -v "$PACKAGE_FILE:/tmp/cicada.deb:ro" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -p 4567:4567 \
    debian:11-slim \
    sleep infinity

sleep 2

# Installer tout
echo -e "${YELLOW}Installation des dépendances...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    apt-get update -qq && \
    apt-get install -y -qq \
        curl gnupg2 systemd systemd-sysv dbus \
        docker.io docker-compose python3 python3-pip sudo \
        > /dev/null 2>&1
"

# Démarrer systemd
docker exec -d "$CONTAINER_NAME" /lib/systemd/systemd --system-unit=basic.target
sleep 3

# Installer le package
echo -e "${YELLOW}Installation du package...${NC}"
docker exec "$CONTAINER_NAME" dpkg -i /tmp/cicada.deb || \
    docker exec "$CONTAINER_NAME" apt-get install -f -y

# Démarrer le service installer
echo -e "${YELLOW}Démarrage du service installer...${NC}"
docker exec "$CONTAINER_NAME" systemctl start cicada-installer.service || true

sleep 5

# Vérifier que l'interface web répond
echo -e "${YELLOW}Test de l'interface web...${NC}"
if curl -s http://localhost:4567/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Interface web accessible sur http://localhost:4567${NC}"
else
    echo -e "${RED}✗ Interface web non accessible${NC}"
    echo "Logs du service :"
    docker exec "$CONTAINER_NAME" journalctl -u cicada-installer.service --no-pager -n 20 || true
fi

echo ""
echo -e "${GREEN}=== Test terminé ===${NC}"
echo ""
echo "Interface web : http://localhost:4567"
echo "Pour nettoyer : docker rm -f $CONTAINER_NAME"
