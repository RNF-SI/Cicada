#!/bin/bash
# Socle de la VM « hub » : ce que docs/DEPLOIEMENT_HUB.md demande au serveur
# (Docker, Apache + modules proxy) et les images de la version, pré-tirées.
# Les fichiers de déploiement du dépôt sont copiés dans /opt/cicada-hub par
# bench.sh, comme le `git clone` du guide.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
VERSION="$1"
BENCH_DIR="${BENCH_DIR:-/home/ubuntu/bench}"
bash "$BENCH_DIR/guest/prereq-docker.sh"
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin apache2 >/dev/null
systemctl enable --now docker >/dev/null
a2enmod -q proxy proxy_http headers >/dev/null
a2dissite -q 000-default >/dev/null
docker pull -q "ghcr.io/rnf-si/cicada-hub:$VERSION"
docker pull -q postgis/postgis:17-3.5-alpine
mkdir -p /var/log/cicada-hub
echo "Socle hub prêt (cicada-hub:$VERSION)"
