#!/bin/bash
# Ne pas arrêter sur erreur pour certaines commandes
set -e

# Script de test pour l'installation du package CICADA
# Utilise Docker pour créer un environnement isolé

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

# Version dynamique : lire depuis cicada.conf ou utiliser VERSION env var
VERSION="${VERSION:-$(awk -F= '/^VERSION=/{print $2; exit}' "$SCRIPT_DIR/debian/etc/cicada/cicada.conf" 2>/dev/null || echo "0.1.14")}"
PACKAGE_FILE="$BUILD_DIR/cicada_${VERSION}_amd64.deb"
CONTAINER_NAME="cicada-test-install"

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Test d'installation CICADA v${VERSION} ===${NC}"

# Vérifier que le package existe
if [ ! -f "$PACKAGE_FILE" ]; then
    echo -e "${RED}Erreur : Le package $PACKAGE_FILE n'existe pas${NC}"
    echo "Exécutez d'abord : ./build-deb.sh"
    exit 1
fi

# Nettoyer les conteneurs précédents
echo -e "${YELLOW}Nettoyage des conteneurs précédents...${NC}"
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Créer un conteneur Debian
echo -e "${YELLOW}Création du conteneur de test (Debian)...${NC}"
docker run -d \
    --name "$CONTAINER_NAME" \
    --privileged \
    -v "$PACKAGE_FILE:/tmp/cicada.deb:ro" \
    debian:11-slim \
    sleep infinity

# Attendre que le conteneur soit prêt
sleep 2

# Installer les dépendances de base
echo -e "${YELLOW}Installation des dépendances de base...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    apt-get update -qq
    apt-get install -y -qq \
        curl \
        gnupg2 \
        ca-certificates \
        lsb-release \
        python3 \
        python3-pip \
        sudo \
        2>&1 | grep -v '^WARNING' || true
" || {
    echo -e "${RED}Erreur lors de l'installation des dépendances de base${NC}"
    exit 1
}

echo -e "${YELLOW}Installation de Docker (cela peut prendre quelques minutes)...${NC}"
echo -e "${YELLOW}  Étape 1/4 : Configuration du repository...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg 2>&1 || exit 1
    echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \$(lsb_release -cs) stable\" > /etc/apt/sources.list.d/docker.list
" || {
    echo -e "${YELLOW}Installation de Docker échouée, tentative avec docker.io...${NC}"
    docker exec "$CONTAINER_NAME" bash -c "
        apt-get update -qq
        apt-get install -y -qq docker.io docker-compose-plugin 2>&1 | grep -v '^WARNING' || true
    " || {
        echo -e "${YELLOW}Docker non installé. Le test continuera sans Docker (certaines fonctionnalités ne seront pas testées).${NC}"
        DOCKER_INSTALLED=false
    }
    DOCKER_INSTALLED=false
}

if [ "${DOCKER_INSTALLED:-true}" = "true" ]; then
    echo -e "${YELLOW}  Étape 2/4 : Mise à jour des packages...${NC}"
    docker exec "$CONTAINER_NAME" apt-get update -qq || true
    
    echo -e "${YELLOW}  Étape 3/4 : Installation de Docker CE...${NC}"
    docker exec "$CONTAINER_NAME" bash -c "
        apt-get install -y -qq \
            docker-ce \
            docker-ce-cli \
            containerd.io \
            docker-buildx-plugin \
            docker-compose-plugin \
            2>&1 | grep -E '(Get|Hit|Ign|Err|WARN)' | head -20 || true
    " || {
        echo -e "${YELLOW}Installation Docker CE échouée, utilisation de docker.io...${NC}"
        docker exec "$CONTAINER_NAME" bash -c "
            apt-get update -qq
            apt-get install -y -qq docker.io docker-compose-plugin 2>&1 | grep -v '^WARNING' || true
        " || DOCKER_INSTALLED=false
    }
    
    if [ "${DOCKER_INSTALLED:-true}" = "true" ]; then
        echo -e "${YELLOW}  Étape 4/4 : Vérification...${NC}"
        docker exec "$CONTAINER_NAME" docker --version || DOCKER_INSTALLED=false
        docker exec "$CONTAINER_NAME" docker compose version || DOCKER_INSTALLED=false
    fi
fi

# Note: systemd ne fonctionne pas bien dans Docker sans configuration spéciale
# On va simuler les vérifications sans vraiment démarrer systemd
echo -e "${YELLOW}Configuration de l'environnement...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    # Créer un lien symbolique pour systemctl si nécessaire
    mkdir -p /run/systemd/system
"

# Installer le package
echo -e "${YELLOW}Installation du package...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    dpkg -i /tmp/cicada.deb 2>&1 || {
        echo 'Correction des dépendances...'
        apt-get install -f -y 2>&1 | grep -v '^WARNING' || true
    }
" || {
    echo -e "${RED}Erreur lors de l'installation du package${NC}"
    docker exec "$CONTAINER_NAME" bash -c "dpkg -l | grep cicada" || true
    exit 1
}

# Vérifier l'installation
echo -e "${YELLOW}Vérification de l'installation...${NC}"

# Vérifier que les fichiers sont en place
echo -e "${GREEN}Vérification des fichiers :${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    echo '✓ Token d''instance :' && test -f /etc/cicada/instance_token && echo '  OK' || echo '  MANQUANT'
    echo '✓ Configuration :' && test -f /etc/cicada/cicada.conf && echo '  OK' || echo '  MANQUANT'
    echo '✓ Script heartbeat :' && test -f /usr/bin/cicada-heartbeat && echo '  OK' || echo '  MANQUANT'
    echo '✓ Script updater :' && test -f /usr/bin/cicada-updater && echo '  OK' || echo '  MANQUANT'
    echo '✓ Service installer :' && test -f /etc/systemd/system/cicada-installer.service && echo '  OK' || echo '  MANQUANT'
    echo '✓ Service heartbeat :' && test -f /etc/systemd/system/cicada-heartbeat.service && echo '  OK' || echo '  MANQUANT'
    echo '✓ Installer Flask :' && test -d /usr/share/cicada/install && echo '  OK' || echo '  MANQUANT'
"

# Vérifier les services systemd (fichiers seulement, pas l'activation réelle)
echo -e "${GREEN}Vérification des fichiers de services systemd :${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    test -f /etc/systemd/system/cicada-installer.service && echo '✓ cicada-installer.service : fichier présent' || echo '✗ cicada-installer.service : fichier manquant'
    test -f /etc/systemd/system/cicada-heartbeat.service && echo '✓ cicada-heartbeat.service : fichier présent' || echo '✗ cicada-heartbeat.service : fichier manquant'
    test -f /etc/systemd/system/cicada-heartbeat.timer && echo '✓ cicada-heartbeat.timer : fichier présent' || echo '✗ cicada-heartbeat.timer : fichier manquant'
    test -f /etc/systemd/system/cicada-updater.service && echo '✓ cicada-updater.service : fichier présent' || echo '✗ cicada-updater.service : fichier manquant'
    test -f /etc/systemd/system/cicada-updater.path && echo '✓ cicada-updater.path : fichier présent' || echo '✗ cicada-updater.path : fichier manquant'
"

# Tester le script heartbeat
echo -e "${YELLOW}Test du script heartbeat...${NC}"
if docker exec "$CONTAINER_NAME" test -x /usr/bin/cicada-heartbeat; then
    echo -e "${GREEN}✓ Script heartbeat exécutable${NC}"
    # Essayer de l'exécuter (échouera probablement car l'API n'est pas accessible, c'est normal)
    docker exec "$CONTAINER_NAME" python3 /usr/bin/cicada-heartbeat 2>&1 | head -5 || echo -e "${YELLOW}  (Erreur attendue si l'API n'est pas accessible)${NC}"
else
    echo -e "${RED}✗ Script heartbeat non exécutable${NC}"
fi

# Afficher la configuration
echo -e "${GREEN}Configuration installée :${NC}"
docker exec "$CONTAINER_NAME" cat /etc/cicada/cicada.conf

# Afficher le token (pour test)
echo -e "${GREEN}Token d'instance généré :${NC}"
docker exec "$CONTAINER_NAME" cat /etc/cicada/instance_token

echo ""
echo -e "${GREEN}=== Test terminé ===${NC}"
echo ""
echo "Pour accéder au conteneur de test :"
echo "  docker exec -it $CONTAINER_NAME bash"
echo ""
echo "Pour nettoyer :"
echo "  docker rm -f $CONTAINER_NAME"
echo ""
echo "Pour tester l'interface d'installation (nécessite Docker dans Docker) :"
echo "  Note: L'interface web nécessite Docker fonctionnel dans le conteneur"
echo "  Ce test vérifie uniquement l'installation des fichiers et services"
