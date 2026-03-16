#!/bin/bash
# Test de l'interface web d'installation (port 4567)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"
PACKAGE_FILE="$BUILD_DIR/cicada_0.1.12_amd64.deb"
CONTAINER_NAME="cicada-test-web"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== Test de l'interface web d'installation CICADA ===${NC}"

if [ ! -f "$PACKAGE_FILE" ]; then
    echo -e "${RED}Erreur : Le package $PACKAGE_FILE n'existe pas${NC}"
    exit 1
fi

# Nettoyer
echo -e "${YELLOW}Nettoyage des conteneurs précédents...${NC}"
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Préparer sur l'hôte le chemin attendu par le bind mount (init.sql)
# Quand l'installateur lance "docker compose up", le démon Docker (sur l'hôte) monte
# /usr/share/cicada/docker/postgres/init.sql ; ce chemin doit être un FICHIER sur l'hôte.
# Si un répertoire a été créé par erreur (bind mount vers un chemin inexistant), le supprimer.
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -f "$PROJECT_ROOT/docker/postgres/init.sql" ]; then
    echo -e "${YELLOW}Préparation du bind mount init.sql sur l'hôte...${NC}"
    sudo rm -rf /usr/share/cicada/docker/postgres/init.sql
    sudo mkdir -p /usr/share/cicada/docker/postgres
    sudo cp "$PROJECT_ROOT/docker/postgres/init.sql" /usr/share/cicada/docker/postgres/init.sql
    ls -la /usr/share/cicada/docker/postgres/init.sql
fi

# Créer un conteneur avec Docker socket monté (pour Docker-in-Docker)
echo -e "${YELLOW}Création du conteneur de test...${NC}"
docker run -d \
    --name "$CONTAINER_NAME" \
    --privileged \
    -v "$PACKAGE_FILE:/tmp/cicada.deb:ro" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -p 4567:4567 \
    debian:11-slim \
    sleep infinity

sleep 2

# Installer les dépendances minimales AVANT le package
echo -e "${YELLOW}Installation des dépendances...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    apt-get update -qq > /dev/null 2>&1
    apt-get install -y -qq python3 python3-pip curl ca-certificates gnupg lsb-release > /dev/null 2>&1
"

# Installer Docker dans le conteneur (nécessaire pour l'installation complète)
echo -e "${YELLOW}Installation de Docker dans le conteneur...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    # Installer Docker depuis le repository officiel
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo \"deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \$(lsb_release -cs) stable\" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update -qq > /dev/null 2>&1
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin > /dev/null 2>&1
    
    # Vérifier que docker est disponible
    if command -v docker >/dev/null 2>&1; then
        echo '✓ Docker installé et disponible'
        docker --version
        docker compose version
    else
        echo '✗ Docker installé mais commande non trouvée'
        which docker || echo 'docker non trouvé dans PATH'
        ls -la /usr/bin/docker* || true
    fi
" || {
    echo -e "${YELLOW}Note: Installation de Docker échouée, mais on continue avec le socket monté${NC}"
}

# Installer le package (sans Docker pour le test rapide)
echo -e "${YELLOW}Installation du package...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    # Installer avec --force-depends pour ignorer les dépendances Docker
    dpkg --force-depends --force-confnew -i /tmp/cicada.deb 2>&1 | grep -v '^WARNING' || true
    
    # Forcer la configuration même si elle a échoué partiellement
    dpkg --configure --force-depends cicada 2>&1 | grep -v '^WARNING' || true
    
    # Vérifier que les fichiers sont bien installés
    if [ ! -d /usr/share/cicada/install ]; then
        echo 'ATTENTION: Les fichiers ne semblent pas installés'
        echo 'Vérification du statut du package:'
        dpkg -l | grep cicada || true
        echo 'Tentative de réparation...'
        dpkg --configure -a || true
        # Si toujours pas là, extraire manuellement
        if [ ! -d /usr/share/cicada/install ]; then
            echo 'Extraction manuelle des fichiers...'
            dpkg-deb -x /tmp/cicada.deb /tmp/extract 2>&1 || true
            cp -r /tmp/extract/usr/share/cicada /usr/share/ 2>&1 || true
        fi
    fi
"

# Vérifier que les fichiers sont en place
echo -e "${YELLOW}Vérification des fichiers...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    test -f /usr/share/cicada/install/app.py && echo '✓ app.py présent' || echo '✗ app.py manquant'
    test -f /usr/share/cicada/install/install_service.py && echo '✓ install_service.py présent' || echo '✗ install_service.py manquant'
    test -f /etc/cicada/instance_token && echo '✓ Token généré' || echo '✗ Token manquant'
"

# Installer les dépendances Python si nécessaire
echo -e "${YELLOW}Vérification des dépendances Python...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    if ! python3 -c 'import flask' 2>/dev/null; then
        echo 'Installation de Flask...'
        pip3 install flask python-dotenv requests --quiet
    else
        echo '✓ Flask déjà installé'
    fi
"

# Démarrer l'interface web
echo -e "${YELLOW}Démarrage de l'interface web d'installation...${NC}"
echo -e "${BLUE}L'interface sera accessible sur : http://localhost:4567${NC}"
echo ""

# Vérifier que les fichiers sont bien installés
echo -e "${YELLOW}Vérification de l'installation des fichiers...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    if [ ! -d /usr/share/cicada/install ]; then
        echo 'Erreur: répertoire /usr/share/cicada/install introuvable'
        echo 'Contenu de /usr/share/cicada:'
        ls -la /usr/share/cicada/ || true
        exit 1
    fi
    echo 'Fichiers dans /usr/share/cicada/install:'
    ls -la /usr/share/cicada/install/ || true
"

# Vérifier que les fichiers sont bien installés
echo -e "${YELLOW}Vérification de l'installation des fichiers...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    if [ ! -d /usr/share/cicada/install ]; then
        echo 'Erreur: répertoire /usr/share/cicada/install introuvable'
        echo 'Contenu de /usr/share/cicada:'
        ls -la /usr/share/cicada/ || true
        exit 1
    fi
    echo 'Fichiers dans /usr/share/cicada/install:'
    ls -la /usr/share/cicada/install/ || true
    test -f /usr/share/cicada/install/app.py && echo '✓ app.py présent' || echo '✗ app.py manquant'
    test -f /usr/share/cicada/install/install_service.py && echo '✓ install_service.py présent' || echo '✗ install_service.py manquant'
" || {
    echo -e "${RED}Les fichiers ne sont pas installés correctement${NC}"
    exit 1
}

# Vérifier que Python3 est toujours disponible
echo -e "${YELLOW}Vérification de Python3...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    if ! command -v python3 >/dev/null 2>&1; then
        echo 'Python3 non trouvé, réinstallation...'
        apt-get update -qq > /dev/null 2>&1
        apt-get install -y -qq python3 python3-pip > /dev/null 2>&1
    fi
    python3 --version
    which python3
"

# S'assurer que Python 3 est installé et disponible
echo -e "${YELLOW}Vérification de Python 3...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    if ! command -v python3 >/dev/null 2>&1; then
        echo 'Installation de Python 3...'
        apt-get update -qq > /dev/null 2>&1
        apt-get install -y -qq python3 python3-pip > /dev/null 2>&1
    fi
    python3 --version || echo 'ERREUR: python3 non disponible'
    which python3 || echo 'ERREUR: python3 non trouvé dans PATH'
"

# Vérifier que Flask est installé
echo -e "${YELLOW}Vérification de Flask...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    if ! python3 -c 'import flask' 2>/dev/null; then
        echo 'Installation de Flask...'
        pip3 install flask python-dotenv requests --quiet
    fi
    python3 -c 'import flask; print(\"Flask version:\", flask.__version__)' || echo 'ERREUR: Flask non disponible'
"

# Lancer Flask en arrière-plan (accessible depuis l'extérieur)
echo -e "${YELLOW}Lancement de Flask...${NC}"
docker exec -d "$CONTAINER_NAME" bash -c "
    cd /usr/share/cicada/install
    export FLASK_APP=app.py
    export FLASK_HOST=0.0.0.0
    export FLASK_PORT=4567
    python3 /usr/share/cicada/install/app.py > /tmp/cicada-installer.log 2>&1
"

# Attendre que Flask démarre
sleep 3

# Vérifier que l'interface répond
echo -e "${YELLOW}Vérification de l'interface web...${NC}"
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
    echo -e "${YELLOW}Pour voir les logs :${NC}"
    echo "  docker exec $CONTAINER_NAME tail -f /tmp/cicada-installer.log"
    echo ""
    echo -e "${YELLOW}Pour arrêter le conteneur :${NC}"
    echo "  docker rm -f $CONTAINER_NAME"
    echo ""
    echo -e "${YELLOW}Note :${NC} Docker est installé dans le conteneur pour permettre l'installation complète."
    echo ""
    echo -e "${GREEN}Appuyez sur Ctrl+C pour arrêter le serveur...${NC}"
    echo ""
    
    # Afficher les logs en temps réel
    docker exec "$CONTAINER_NAME" tail -f /tmp/cicada-installer.log
else
    echo -e "${RED}✗ Interface web non accessible${NC}"
    echo "Logs :"
    docker exec "$CONTAINER_NAME" cat /tmp/cicada-installer.log
    echo ""
    echo "Pour nettoyer : docker rm -f $CONTAINER_NAME"
fi
