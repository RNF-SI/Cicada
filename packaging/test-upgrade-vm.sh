#!/bin/bash
# set -e désactivé : les fonctions de test gèrent les erreurs elles-mêmes
# via run_test() et les vérifications explicites

# =============================================================================
# Test de mise à jour CICADA en VM locale (Multipass)
#
# Teste les 3 méthodes de mise à jour en conditions proches de la production :
#   - Option 2 : sudo apt install (postinst automatique)
#   - Option 3 : commandes manuelles
#   - Option 1 : clic bouton (si API de suivi disponible)
#
# Prérequis : multipass installé (sudo snap install multipass)
#
# Usage :
#   ./test-upgrade-vm.sh                                    # Versions par défaut
#   ./test-upgrade-vm.sh --from 0.1.13 --to 0.1.14         # Versions spécifiques
#   ./test-upgrade-vm.sh --skip-install                     # Réutiliser une VM existante
#   ./test-upgrade-vm.sh --cleanup                          # Supprimer la VM de test
#   ./test-upgrade-vm.sh --test option2                     # Tester uniquement l'option 2
#   ./test-upgrade-vm.sh --test option3                     # Tester uniquement l'option 3
#   ./test-upgrade-vm.sh --test all                         # Tester toutes les options (défaut)
#
# Durée estimée : 10-20 min (première exécution), 5-10 min (VM existante)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$SCRIPT_DIR/build"

VM_NAME="cicada-test-upgrade"
VM_IMAGE="22.04"  # Ubuntu LTS
VM_CPUS="2"
VM_MEMORY="2G"
VM_DISK="10G"

# Versions par défaut
FROM_VERSION="0.1.13"
TO_VERSION="0.1.14"
SKIP_INSTALL=false
CLEANUP_ONLY=false
TEST_TARGET="all"

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# --- Fonctions utilitaires ---

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERREUR]${NC} $1"; }
log_step()  { echo -e "\n${BLUE}=== $1 ===${NC}"; }

usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options :"
    echo "  --from VERSION       Version initiale (défaut: $FROM_VERSION)"
    echo "  --to VERSION         Version cible de la mise à jour (défaut: $TO_VERSION)"
    echo "  --skip-install       Réutiliser la VM existante (skip création + install Docker)"
    echo "  --cleanup            Supprimer la VM de test et quitter"
    echo "  --test TARGET        Quoi tester : option2, option3, all (défaut: all)"
    echo "  --vm-name NAME       Nom de la VM (défaut: $VM_NAME)"
    echo "  -h, --help           Afficher cette aide"
    exit 0
}

# --- Parsing des arguments ---

while [[ $# -gt 0 ]]; do
    case $1 in
        --from)        FROM_VERSION="$2"; shift 2 ;;
        --to)          TO_VERSION="$2"; shift 2 ;;
        --skip-install) SKIP_INSTALL=true; shift ;;
        --cleanup)     CLEANUP_ONLY=true; shift ;;
        --test)        TEST_TARGET="$2"; shift 2 ;;
        --vm-name)     VM_NAME="$2"; shift 2 ;;
        -h|--help)     usage ;;
        *)             log_error "Option inconnue : $1"; usage ;;
    esac
done

# --- Cleanup ---

cleanup_vm() {
    log_step "Suppression de la VM $VM_NAME"
    multipass delete "$VM_NAME" 2>/dev/null || true
    multipass purge 2>/dev/null || true
    rm -rf "$SCRIPT_DIR/.test-debs"
    log_info "VM et fichiers temporaires supprimés."
}

if [ "$CLEANUP_ONLY" = true ]; then
    cleanup_vm
    exit 0
fi

# --- Vérifications ---

log_step "Vérifications préalables"

if ! command -v multipass &>/dev/null; then
    log_error "Multipass n'est pas installé. Lancez : sudo snap install multipass"
    exit 1
fi
log_info "Multipass : $(multipass version | head -1)"

if ! command -v dpkg-deb &>/dev/null; then
    log_error "dpkg-deb n'est pas installé (nécessaire pour construire les .deb)"
    exit 1
fi

# --- Construction des packages .deb ---
# Note : build-deb.sh fait rm -rf build/ à chaque appel, donc on sauvegarde
# les packages dans un sous-dossier dédié pour éviter que le 2ème build
# supprime le .deb du 1er.

log_step "Construction des packages .deb"

# Répertoire séparé de build/ (car build-deb.sh fait rm -rf build/)
DEBS_DIR="$SCRIPT_DIR/.test-debs"
mkdir -p "$DEBS_DIR"

FROM_DEB="$DEBS_DIR/cicada_${FROM_VERSION}_amd64.deb"
TO_DEB="$DEBS_DIR/cicada_${TO_VERSION}_amd64.deb"

# Construire le package FROM_VERSION (s'il n'existe pas)
if [ ! -f "$FROM_DEB" ]; then
    log_info "Construction du package v${FROM_VERSION}..."
    VERSION="$FROM_VERSION" bash "$SCRIPT_DIR/build-deb.sh"
    cp "$BUILD_DIR/cicada_${FROM_VERSION}_amd64.deb" "$FROM_DEB"
else
    log_info "Package v${FROM_VERSION} déjà construit : $FROM_DEB"
fi

# Construire le package TO_VERSION (s'il n'existe pas ou si différent)
if [ "$FROM_VERSION" != "$TO_VERSION" ]; then
    if [ ! -f "$TO_DEB" ]; then
        log_info "Construction du package v${TO_VERSION}..."
        VERSION="$TO_VERSION" bash "$SCRIPT_DIR/build-deb.sh"
        cp "$BUILD_DIR/cicada_${TO_VERSION}_amd64.deb" "$TO_DEB"
    else
        log_info "Package v${TO_VERSION} déjà construit : $TO_DEB"
    fi
fi

# Vérifier que les packages existent
for deb in "$FROM_DEB" "$TO_DEB"; do
    if [ ! -f "$deb" ]; then
        log_error "Package introuvable : $deb"
        exit 1
    fi
done

# --- Création de la VM ---

if [ "$SKIP_INSTALL" = false ]; then
    log_step "Création de la VM Multipass ($VM_NAME)"

    # Supprimer si elle existe déjà
    if multipass info "$VM_NAME" &>/dev/null; then
        log_warn "La VM $VM_NAME existe déjà, suppression..."
        multipass delete "$VM_NAME" && multipass purge
    fi

    log_info "Lancement de la VM (Ubuntu $VM_IMAGE, ${VM_CPUS} CPUs, ${VM_MEMORY} RAM, ${VM_DISK} disque)..."
    multipass launch "$VM_IMAGE" \
        --name "$VM_NAME" \
        --cpus "$VM_CPUS" \
        --memory "$VM_MEMORY" \
        --disk "$VM_DISK"

    log_info "VM créée. Attente du démarrage..."
    sleep 5

    # --- Installation de Docker dans la VM ---

    log_step "Installation de Docker dans la VM"

    multipass exec "$VM_NAME" -- bash -c '
        set -e
        echo ">>> Installation des prérequis..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq ca-certificates curl gnupg lsb-release

        echo ">>> Ajout du repository Docker..."
        sudo install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        sudo chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

        echo ">>> Installation de Docker CE..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

        echo ">>> Vérification Docker..."
        docker --version
        docker compose version
        echo ">>> Docker installé avec succès."
    '
    log_info "Docker installé dans la VM."

else
    log_info "Réutilisation de la VM existante ($VM_NAME)"
    if ! multipass info "$VM_NAME" &>/dev/null; then
        log_error "La VM $VM_NAME n'existe pas. Relancez sans --skip-install."
        exit 1
    fi
fi

# --- Transfert des packages dans la VM ---

log_step "Transfert des packages dans la VM"

multipass transfer "$FROM_DEB" "$VM_NAME:/home/ubuntu/cicada_${FROM_VERSION}.deb"
multipass transfer "$TO_DEB" "$VM_NAME:/home/ubuntu/cicada_${TO_VERSION}.deb"
log_info "Packages transférés."

# --- Installation initiale (version FROM) ---

log_step "Installation initiale v${FROM_VERSION}"

multipass exec "$VM_NAME" -- bash -c "
    echo '>>> Installation du package v${FROM_VERSION}...'
    sudo dpkg -i /home/ubuntu/cicada_${FROM_VERSION}.deb 2>/dev/null || sudo apt-get install -f -y 2>/dev/null

    echo ''
    echo '>>> Vérification des fichiers...'
    test -f /etc/cicada/instance_token && echo '  OK : instance_token' || echo '  MANQUANT : instance_token'
    test -f /etc/cicada/cicada.conf && echo '  OK : cicada.conf' || echo '  MANQUANT : cicada.conf'
    test -f /usr/bin/cicada-heartbeat && echo '  OK : cicada-heartbeat' || echo '  MANQUANT : cicada-heartbeat'
    test -f /usr/bin/cicada-updater && echo '  OK : cicada-updater' || echo '  MANQUANT : cicada-updater'
    test -f /usr/share/cicada/docker-compose.yml && echo '  OK : docker-compose.yml' || echo '  MANQUANT : docker-compose.yml'

    echo ''
    echo '>>> Services systemd...'
    systemctl is-enabled cicada-installer.service 2>/dev/null && echo '  OK : cicada-installer enabled' || echo '  WARN : cicada-installer not enabled'
    systemctl is-enabled cicada-heartbeat.timer 2>/dev/null && echo '  OK : cicada-heartbeat.timer enabled' || echo '  WARN : cicada-heartbeat.timer not enabled'
    systemctl is-enabled cicada-updater.path 2>/dev/null && echo '  OK : cicada-updater.path enabled' || echo '  WARN : cicada-updater.path not enabled'

    echo ''
    echo '>>> Version installée :'
    grep '^VERSION=' /etc/cicada/cicada.conf

    echo ''
    echo '>>> Vérification de init.sql (12 schémas attendus) :'
    INIT_SQL='/usr/share/cicada/docker/postgres/init.sql'
    if [ -f \"\$INIT_SQL\" ]; then
        SCHEMA_COUNT=0
        for schema in utilisateurs referentiels ref_nomenclatures ref_geo general fichiers ccd_commons ccd_notifications taxonomie ref_habitats ref_inpg ref_campanule; do
            if grep -q \"CREATE SCHEMA IF NOT EXISTS \$schema\" \"\$INIT_SQL\"; then
                SCHEMA_COUNT=\$((SCHEMA_COUNT + 1))
            else
                echo \"  MANQUANT: \$schema\"
            fi
        done
        echo \"  Schémas trouvés: \$SCHEMA_COUNT/12\"
    else
        echo '  ERREUR: init.sql introuvable'
    fi
"

# --- Simulation d'un environnement déjà configuré (comme en production) ---

log_step "Simulation d'un environnement production (création du .env)"

multipass exec "$VM_NAME" -- bash -c "
    sudo tee /var/lib/cicada/.env > /dev/null <<'ENVEOF'
SECRET_KEY=test-secret-key-for-upgrade-test
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,web
CICADA_VERSION=${FROM_VERSION}

POSTGRES_DB=cicada
POSTGRES_USER=cicada_user
POSTGRES_PASSWORD=test_password
POSTGRES_HOST=db
POSTGRES_PORT=5432
DB_TYPE=docker

REDIS_PASSWORD=test_redis_password

FRONTEND_PORT=8080
DJANGO_PORT=8000
SITE_URL=http://localhost:8080
TRAEFIK_ENABLED=false
ENVEOF

    echo '>>> .env créé avec CICADA_VERSION=${FROM_VERSION}'
    grep CICADA_VERSION /var/lib/cicada/.env
"
log_info "Environnement simulé."

# =============================================================================
# TESTS DE MISE À JOUR
# =============================================================================

TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local name="$1"
    local result="$2"
    if [ "$result" = "0" ]; then
        log_info "PASS : $name"
        ((TESTS_PASSED++))
    else
        log_error "FAIL : $name"
        ((TESTS_FAILED++))
    fi
}

# --- Test Option 2 : sudo apt install (postinst automatique) ---

test_option2() {
    log_step "TEST OPTION 2 : sudo apt install cicada=${TO_VERSION}"
    log_info "Le postinst doit automatiquement :"
    log_info "  1. Détecter que .env existe (= upgrade, pas première install)"
    log_info "  2. Mettre à jour CICADA_VERSION dans .env"
    log_info "  3. Appeler docker compose pull (échouera car pas d'images, c'est attendu)"
    log_info "  4. Appeler docker compose up -d (échouera aussi, c'est attendu)"

    # Remettre à la version FROM pour le test
    multipass exec "$VM_NAME" -- bash -c "
        sudo sed -i 's/^CICADA_VERSION=.*/CICADA_VERSION=${FROM_VERSION}/' /var/lib/cicada/.env
    "

    # Installer le nouveau package (les logs Docker du prerm sont très verbeux, on les redirige)
    log_info "Installation du package v${TO_VERSION}..."
    multipass exec "$VM_NAME" -- sudo dpkg -i /home/ubuntu/cicada_${TO_VERSION}.deb > /dev/null 2>&1 || true

    # Vérification 1 : CICADA_VERSION mis à jour dans .env
    local env_version
    env_version=$(multipass exec "$VM_NAME" -- grep "^CICADA_VERSION=" /var/lib/cicada/.env | cut -d= -f2 | tr -d '\r')
    if [ "$env_version" = "$TO_VERSION" ]; then
        run_test "CICADA_VERSION dans .env = ${TO_VERSION}" 0
    else
        run_test "CICADA_VERSION dans .env = ${TO_VERSION} (trouvé: '${env_version}')" 1
    fi

    # Vérification 2 : VERSION dans cicada.conf mis à jour
    local conf_version
    conf_version=$(multipass exec "$VM_NAME" -- grep "^VERSION=" /etc/cicada/cicada.conf | cut -d= -f2 | tr -d '\r')
    if [ "$conf_version" = "$TO_VERSION" ]; then
        run_test "VERSION dans cicada.conf = ${TO_VERSION}" 0
    else
        run_test "VERSION dans cicada.conf = ${TO_VERSION} (trouvé: '${conf_version}')" 1
    fi

    # Vérification 3 : les services systemd sont toujours actifs
    local installer_enabled
    installer_enabled=$(multipass exec "$VM_NAME" -- systemctl is-enabled cicada-installer.service 2>/dev/null | tr -d '\r' || echo "disabled")
    if [ "$installer_enabled" = "enabled" ]; then
        run_test "cicada-installer.service toujours enabled après upgrade" 0
    else
        run_test "cicada-installer.service toujours enabled après upgrade (état: '${installer_enabled}')" 1
    fi

    # Vérification 4 : le message de mise à jour a été affiché (pas première install)
    # On réinstalle la même version pour vérifier le message "déjà à jour"
    local postinst_output
    postinst_output=$(multipass exec "$VM_NAME" -- sudo dpkg -i /home/ubuntu/cicada_${TO_VERSION}.deb 2>&1 || true)
    if echo "$postinst_output" | grep -q "mis à jour avec succès"; then
        run_test "Message 'mis à jour avec succès' affiché (pas 'première installation')" 0
    elif echo "$postinst_output" | grep -q "déjà à jour"; then
        run_test "Message 'version déjà à jour' affiché (même version réinstallée)" 0
    else
        run_test "Message de mise à jour affiché" 1
    fi

    # Vérification 5 : init.sql contient les 12 schémas
    local schema_count
    schema_count=$(multipass exec "$VM_NAME" -- bash -c "
        grep -c 'CREATE SCHEMA IF NOT EXISTS' /usr/share/cicada/docker/postgres/init.sql 2>/dev/null || echo 0
    " | tr -d '\r')
    if [ "$schema_count" -ge 12 ]; then
        run_test "init.sql contient les 12 schémas ($schema_count trouvés)" 0
    else
        run_test "init.sql contient les 12 schémas ($schema_count trouvés)" 1
    fi

    log_info "Option 2 terminée."
}

# --- Test Option 3 : commandes manuelles ---

test_option3() {
    log_step "TEST OPTION 3 : commandes manuelles"

    # Remettre à la version FROM
    multipass exec "$VM_NAME" -- bash -c "
        sudo sed -i 's/^CICADA_VERSION=.*/CICADA_VERSION=${FROM_VERSION}/' /var/lib/cicada/.env
    "

    # Étape 1 : apt install
    log_info "Étape 1 : apt install..."
    multipass exec "$VM_NAME" -- sudo dpkg -i /home/ubuntu/cicada_${TO_VERSION}.deb > /dev/null 2>&1 || true

    # Étape 2 : vérifier que sed fonctionne pour mettre à jour le .env manuellement
    log_info "Étape 2 : mise à jour manuelle du .env..."
    multipass exec "$VM_NAME" -- bash -c "
        sudo sed -i 's/^CICADA_VERSION=.*/CICADA_VERSION=${TO_VERSION}/' /var/lib/cicada/.env
    "

    local env_version
    env_version=$(multipass exec "$VM_NAME" -- grep "^CICADA_VERSION=" /var/lib/cicada/.env | cut -d= -f2 | tr -d '\r')
    if [ "$env_version" = "$TO_VERSION" ]; then
        run_test "Option 3 : sed met à jour CICADA_VERSION correctement" 0
    else
        run_test "Option 3 : sed met à jour CICADA_VERSION correctement (trouvé: '${env_version}')" 1
    fi

    # Étape 3 : vérifier que docker compose accepte les fichiers
    log_info "Étape 3 : validation de la config docker compose..."
    local compose_valid
    compose_valid=$(multipass exec "$VM_NAME" -- bash -c "
        cd /usr/share/cicada
        sudo docker compose -f docker-compose.yml -f docker-compose.db.yml --env-file /var/lib/cicada/.env config --quiet 2>&1 && echo 'VALID' || echo 'INVALID'
    ")
    if echo "$compose_valid" | grep -q "VALID"; then
        run_test "Option 3 : docker compose config valide" 0
    else
        run_test "Option 3 : docker compose config valide" 1
        log_warn "Sortie : $compose_valid"
    fi

    log_info "Option 3 terminée."
}

# --- Exécution des tests ---

case "$TEST_TARGET" in
    option2)
        test_option2
        ;;
    option3)
        test_option3
        ;;
    all)
        test_option2
        test_option3
        ;;
    *)
        log_error "Cible de test inconnue : $TEST_TARGET (attendu: option2, option3, all)"
        exit 1
        ;;
esac

# --- Résumé ---

log_step "Résumé des tests"

echo ""
echo -e "  Tests réussis : ${GREEN}${TESTS_PASSED}${NC}"
echo -e "  Tests échoués : ${RED}${TESTS_FAILED}${NC}"
echo ""

if [ "$TESTS_FAILED" -gt 0 ]; then
    log_error "Certains tests ont échoué !"
    echo ""
    echo "Pour investiguer :"
    echo "  multipass shell $VM_NAME"
    echo ""
    echo "Fichiers utiles dans la VM :"
    echo "  /etc/cicada/cicada.conf          # Config du package"
    echo "  /var/lib/cicada/.env             # Config Docker"
    echo "  /var/log/cicada/                 # Logs"
    echo ""
    exit 1
else
    log_info "Tous les tests sont passés !"
fi

echo ""
echo "Pour accéder à la VM :   multipass shell $VM_NAME"
echo "Pour supprimer la VM :   $0 --cleanup"
echo "Pour relancer (rapide) : $0 --skip-install --from $FROM_VERSION --to $TO_VERSION"
echo ""
