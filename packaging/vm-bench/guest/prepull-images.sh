#!/bin/bash
# Pré-télécharge les images Docker dans la VM de base, pour ne pas repayer
# ~2 Go à chaque scénario. L'installateur refait son `docker compose pull`
# (qui vérifie alors seulement l'accès au registre).
# Installe Docker pour cela : sans --no-prepull, le scénario ne vérifie donc
# plus que le paquet sait tirer Docker par ses dépendances.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
VERSION="$1"

apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin >/dev/null
systemctl enable --now docker >/dev/null

for image in \
    "ghcr.io/rnf-si/cicada-backend:$VERSION" \
    "ghcr.io/rnf-si/cicada-frontend:$VERSION" \
    "redis:7-alpine" \
    "postgis/postgis:17-3.5-alpine"; do
    echo "pull $image"
    docker pull -q "$image"
done
