#!/bin/bash
# Prérequis Docker tels qu'un opérateur doit les installer AVANT le paquet
# (dépôt officiel Docker : le .deb dépend de docker-ce, absent des dépôts
# Debian/Ubuntu — cf. #221). Rejoue la procédure décrite dans l'issue.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

. /etc/os-release
case "$ID" in
    debian|ubuntu) ;;
    *) echo "OS non géré : $ID"; exit 1 ;;
esac

apt-get update -qq
apt-get install -y -qq ca-certificates curl gnupg >/dev/null
install -m 0755 -d /etc/apt/keyrings
curl -fsSL "https://download.docker.com/linux/$ID/gpg" | gpg --dearmor --yes -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$ID $VERSION_CODENAME stable" \
    > /etc/apt/sources.list.d/docker.list
apt-get update -qq
# Docker lui-même n'est PAS installé ici : c'est au paquet cicada de le tirer
# via ses dépendances (on teste justement qu'elles se résolvent).
echo "Dépôt Docker configuré pour $ID $VERSION_CODENAME"
