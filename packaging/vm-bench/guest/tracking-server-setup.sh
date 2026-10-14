#!/bin/bash
# Socle de la VM « tracking » (serveur de suivi) : ce que demandent
# tracking-api/INSTALLATION.md (PostgreSQL, Python, Apache) et le dépôt APT
# (reprepro, GnuPG). Le code de tracking-api est déployé au moment du run.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq postgresql python3-venv python3-pip apache2 reprepro gnupg curl >/dev/null
a2enmod -q proxy proxy_http headers >/dev/null
a2dissite -q 000-default >/dev/null
systemctl enable --now postgresql >/dev/null
echo "Socle tracking prêt : PostgreSQL $(runuser -u postgres -- psql -Atc 'show server_version'), reprepro $(reprepro --version 2>&1 | head -1)"
