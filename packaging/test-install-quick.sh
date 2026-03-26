#!/bin/bash
# Test rapide - vérifie uniquement l'installation des fichiers (sans Docker)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

# Version dynamique : lire depuis cicada.conf ou utiliser VERSION env var
VERSION="${VERSION:-$(awk -F= '/^VERSION=/{print $2; exit}' "$SCRIPT_DIR/debian/etc/cicada/cicada.conf" 2>/dev/null || echo "0.1.15")}"
PACKAGE_FILE="$BUILD_DIR/cicada_${VERSION}_amd64.deb"
CONTAINER_NAME="cicada-test-quick"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Test rapide d'installation CICADA v${VERSION} ===${NC}"

if [ ! -f "$PACKAGE_FILE" ]; then
    echo -e "${RED}Erreur : Le package $PACKAGE_FILE n'existe pas${NC}"
    echo "Exécutez d'abord : ./build-deb.sh"
    exit 1
fi

# Nettoyer
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Créer un conteneur minimal
echo -e "${YELLOW}Création du conteneur de test...${NC}"
docker run -d \
    --name "$CONTAINER_NAME" \
    -v "$PACKAGE_FILE:/tmp/cicada.deb:ro" \
    debian:11-slim \
    sleep infinity

sleep 2

# Installer uniquement les dépendances minimales
echo -e "${YELLOW}Installation des dépendances minimales...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    apt-get update -qq > /dev/null 2>&1
    apt-get install -y -qq python3 python3-pip curl > /dev/null 2>&1
"

# Installer le package (sans Docker, donc certaines dépendances échoueront)
echo -e "${YELLOW}Installation du package (mode --force-depends)...${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    dpkg --force-depends -i /tmp/cicada.deb 2>&1 | grep -v '^WARNING' || true
"

# Vérifier les fichiers installés
echo -e "${GREEN}Vérification des fichiers installés :${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    echo 'Fichiers système :'
    test -f /etc/cicada/instance_token && echo '  ✓ /etc/cicada/instance_token' || echo '  ✗ /etc/cicada/instance_token'
    test -f /etc/cicada/cicada.conf && echo '  ✓ /etc/cicada/cicada.conf' || echo '  ✗ /etc/cicada/cicada.conf'
    echo ''
    echo 'Scripts :'
    test -f /usr/bin/cicada-heartbeat && echo '  ✓ /usr/bin/cicada-heartbeat' || echo '  ✗ /usr/bin/cicada-heartbeat'
    test -f /usr/bin/cicada-updater && echo '  ✓ /usr/bin/cicada-updater' || echo '  ✗ /usr/bin/cicada-updater'
    echo ''
    echo 'Services systemd :'
    test -f /etc/systemd/system/cicada-installer.service && echo '  ✓ cicada-installer.service' || echo '  ✗ cicada-installer.service'
    test -f /etc/systemd/system/cicada-heartbeat.service && echo '  ✓ cicada-heartbeat.service' || echo '  ✗ cicada-heartbeat.service'
    test -f /etc/systemd/system/cicada-heartbeat.timer && echo '  ✓ cicada-heartbeat.timer' || echo '  ✗ cicada-heartbeat.timer'
    test -f /etc/systemd/system/cicada-updater.service && echo '  ✓ cicada-updater.service' || echo '  ✗ cicada-updater.service'
    test -f /etc/systemd/system/cicada-updater.path && echo '  ✓ cicada-updater.path' || echo '  ✗ cicada-updater.path'
    echo ''
    echo 'Fichiers de l'\''installer :'
    test -d /usr/share/cicada/install && echo '  ✓ /usr/share/cicada/install' || echo '  ✗ /usr/share/cicada/install'
    test -f /usr/share/cicada/install/app.py && echo '  ✓ app.py' || echo '  ✗ app.py'
    test -f /usr/share/cicada/install/install_service.py && echo '  ✓ install_service.py' || echo '  ✗ install_service.py'
    test -f /usr/share/cicada/docker-compose.yml && echo '  ✓ docker-compose.yml' || echo '  ✗ docker-compose.yml'
    test -f /usr/share/cicada/docker-compose.db.yml && echo '  ✓ docker-compose.db.yml' || echo '  ✗ docker-compose.db.yml'
    test -f /usr/share/cicada/docker-compose.traefik.yml && echo '  ✓ docker-compose.traefik.yml' || echo '  ✗ docker-compose.traefik.yml'
    test -f /usr/share/cicada/docker-compose.frontend-ports.yml && echo '  ✓ docker-compose.frontend-ports.yml' || echo '  ✗ docker-compose.frontend-ports.yml'
    test -f /usr/share/cicada/docker/postgres/init.sql && echo '  ✓ docker/postgres/init.sql' || echo '  ✗ docker/postgres/init.sql'
"

# Vérifier que init.sql contient tous les schémas requis
echo -e "${GREEN}Vérification de init.sql (schémas) :${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    INIT_SQL='/usr/share/cicada/docker/postgres/init.sql'
    if [ ! -f \"\$INIT_SQL\" ]; then
        echo '  ✗ init.sql introuvable'
        exit 1
    fi
    PASS=0
    FAIL=0
    for schema in utilisateurs referentiels ref_nomenclatures ref_geo general fichiers ccd_commons ccd_notifications taxonomie ref_habitats ref_inpg ref_campanule; do
        if grep -q \"CREATE SCHEMA IF NOT EXISTS \$schema\" \"\$INIT_SQL\"; then
            echo \"  ✓ Schéma \$schema\"
            PASS=\$((PASS + 1))
        else
            echo \"  ✗ Schéma \$schema MANQUANT\"
            FAIL=\$((FAIL + 1))
        fi
    done
    echo \"\"
    echo \"  Schémas: \$PASS/12 trouvés\"
    [ \$FAIL -eq 0 ] && echo '  ✓ Tous les schémas sont présents' || echo '  ✗ Des schémas manquent !'
"

# Vérifier que init.sql contient les extensions requises
echo -e "${GREEN}Vérification de init.sql (extensions) :${NC}"
docker exec "$CONTAINER_NAME" bash -c "
    INIT_SQL='/usr/share/cicada/docker/postgres/init.sql'
    for ext in postgis uuid-ossp pg_trgm unaccent; do
        if grep -q \"\$ext\" \"\$INIT_SQL\"; then
            echo \"  ✓ Extension \$ext\"
        else
            echo \"  ✗ Extension \$ext MANQUANTE\"
        fi
    done
"

# Afficher la configuration
echo -e "${GREEN}Configuration :${NC}"
docker exec "$CONTAINER_NAME" cat /etc/cicada/cicada.conf 2>/dev/null || echo "  (non accessible)"

# Afficher le token
echo -e "${GREEN}Token d'instance :${NC}"
docker exec "$CONTAINER_NAME" cat /etc/cicada/instance_token 2>/dev/null || echo "  (non accessible)"

echo ""
echo -e "${GREEN}=== Test rapide terminé ===${NC}"
echo ""
echo "Pour un test complet avec Docker : ./test-install.sh"
echo "Pour nettoyer : docker rm -f $CONTAINER_NAME"
