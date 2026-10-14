# Fonctions shell communes aux scripts du paquet (postinst, prerm…).
# shellcheck shell=bash

CICADA_ENV_FILE="${CICADA_ENV_FILE:-/var/lib/cicada/.env}"
CICADA_COMPOSE_DIR="${CICADA_COMPOSE_DIR:-/usr/share/cicada}"

# Arguments -f de docker compose selon le .env : base, + db si la base est en
# conteneur, + traefik OU exposition du port frontend. Même logique que
# l'installateur web (install_service.py) et l'updater.
compose_files_args() {
    local db_type="" traefik_enabled=""
    if [ -f "$CICADA_ENV_FILE" ]; then
        db_type="$(awk -F= '/^DB_TYPE=/{print $2; exit}' "$CICADA_ENV_FILE")"
        traefik_enabled="$(awk -F= '/^TRAEFIK_ENABLED=/{print tolower($2); exit}' "$CICADA_ENV_FILE")"
    fi
    local args="-f $CICADA_COMPOSE_DIR/docker-compose.yml"
    if [ "${db_type:-docker}" = "docker" ]; then
        args="$args -f $CICADA_COMPOSE_DIR/docker-compose.db.yml"
    fi
    case "${traefik_enabled:-false}" in
        true|1|yes) args="$args -f $CICADA_COMPOSE_DIR/docker-compose.traefik.yml" ;;
        *)          args="$args -f $CICADA_COMPOSE_DIR/docker-compose.frontend-ports.yml" ;;
    esac
    echo "$args"
}
