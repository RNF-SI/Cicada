#!/bin/bash
# Test complet de l'interface web avec Docker fonctionnel

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

# Version dynamique : lire depuis cicada.conf ou utiliser VERSION env var
VERSION="${VERSION:-$(awk -F= '/^VERSION=/{print $2; exit}' "$SCRIPT_DIR/debian/etc/cicada/cicada.conf" 2>/dev/null || echo "0.1.15")}"
PACKAGE_FILE="$BUILD_DIR/cicada_${VERSION}_amd64.deb"
CONTAINER_NAME="cicada-test-web-full"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== Test complet de l'interface web avec Docker ===${NC}"

if [ ! -f "$PACKAGE_FILE" ]; then
    echo -e "${RED}Erreur : Le package $PACKAGE_FILE n'existe pas${NC}"
    exit 1
fi

# Nettoyer
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Créer un conteneur avec Docker socket
echo -e "${YELLOW}Création du conteneur avec Docker...${NC}"
docker run -d \
    --name "$CONTAINER_NAME" \
    --privileged \
    -v "$PACKAGE_FILE:/tmp/cicada.deb:ro" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -p 4567:4567 \
    debian:11-slim \
    sleep infinity

sleep 2

# Installer Docker et dépendances
echo -e "${YELLOW}Installation de Docker et dépendances (cela peut prendre quelques minutes)...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    apt-get update -qq > /dev/null 2>&1
    apt-get install -y -qq \
        curl gnupg2 ca-certificates lsb-release \
        python3 python3-pip \
        > /dev/null 2>&1
    
    # Installer Docker
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>&1
    echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \$(lsb_release -cs) stable\" > /etc/apt/sources.list.d/docker.list
    apt-get update -qq > /dev/null 2>&1
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin > /dev/null 2>&1 || \
    apt-get install -y -qq docker.io docker-compose-plugin > /dev/null 2>&1
"

# Installer le package
echo -e "${YELLOW}Installation du package...${NC}"
docker exec "$CONTAINER_NAME" dpkg -i /tmp/cicada.deb || \
    docker exec "$CONTAINER_NAME" apt-get install -f -y -qq

# Démarrer l'interface web (accessible depuis l'extérieur)
echo -e "${YELLOW}Démarrage de l'interface web...${NC}"
docker exec -d "$CONTAINER_NAME" bash -c "
    cd /usr/share/cicada/install
    export FLASK_HOST=0.0.0.0
    export FLASK_PORT=4567
    python3 app.py > /tmp/cicada-installer.log 2>&1
"

sleep 3

# Vérifier
if curl -s http://localhost:4567/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Interface web accessible !${NC}"
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Interface d'installation prête !${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}Accédez à l'interface :${NC}"
    echo -e "  ${BLUE}http://localhost:4567${NC}"
    echo ""
    echo -e "${YELLOW}Vous pouvez maintenant :${NC}"
    echo "  1. Ouvrir http://localhost:4567 dans votre navigateur"
    echo "  2. Remplir le formulaire d'installation"
    echo "  3. Tester l'installation complète"
    echo ""
    echo -e "${YELLOW}Pour voir les logs :${NC}"
    echo "  docker exec $CONTAINER_NAME tail -f /tmp/cicada-installer.log"
    echo ""
    echo -e "${YELLOW}Pour arrêter :${NC}"
    echo "  docker rm -f $CONTAINER_NAME"
    echo ""
    
    # Suivre les logs
    docker exec "$CONTAINER_NAME" tail -f /tmp/cicada-installer.log
else
    echo -e "${RED}✗ Interface web non accessible${NC}"
    docker exec "$CONTAINER_NAME" cat /tmp/cicada-installer.log
fi
