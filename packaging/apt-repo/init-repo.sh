#!/bin/bash
# =============================================================================
# init-repo.sh — Met en place le dépôt APT de CICADA (reprepro, signé GPG)
#
# Sur le serveur qui héberge le dépôt (TrackingCicada), en root :
#   sudo ./init-repo.sh --key-id <ID_CLE>            # clé GPG déjà présente
#   sudo ./init-repo.sh --generate-key "CICADA <si@rnfrance.org>"
#
# Crée <dir>/conf/distributions (distribution « stable », composant « main »,
# amd64, signée par la clé) et publie la clé publique dans
# <dir>/cicada-repo-key.gpg, l'URL que donne docs/INSTALLATION_GUIDE.md.
# Idempotent. Ne configure pas Apache : voir le vhost proposé en fin de script.
# =============================================================================
set -euo pipefail

REPO_DIR="/var/www/repos/cicada"
KEY_ID=""
GENERATE=""
GNUPGHOME="${GNUPGHOME:-/root/.gnupg}"
export GNUPGHOME

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 0; }
while [ $# -gt 0 ]; do
    case "$1" in
        --dir)          REPO_DIR="$2"; shift 2 ;;
        --key-id)       KEY_ID="$2"; shift 2 ;;
        --generate-key) GENERATE="$2"; shift 2 ;;
        -h|--help)      usage ;;
        *) echo "Option inconnue : $1"; exit 1 ;;
    esac
done
[ "$(id -u)" -eq 0 ] || { echo "À lancer en root"; exit 1; }
command -v reprepro >/dev/null || { echo "reprepro absent : apt install reprepro gnupg"; exit 1; }

mkdir -p "$GNUPGHOME" && chmod 700 "$GNUPGHOME"
if [ -n "$GENERATE" ]; then
    # Clé sans phrase de passe : la publication peut alors se faire sans
    # session interactive (le piège « Inappropriate ioctl » du runbook).
    # Protégez le serveur en conséquence, ou donnez une phrase de passe et
    # publiez avec GPG_TTY=$(tty).
    gpg --batch --pinentry-mode loopback --passphrase '' \
        --quick-gen-key "$GENERATE" rsa4096 sign 5y
    KEY_ID="$(gpg --list-secret-keys --with-colons "$GENERATE" | awk -F: '/^fpr:/{print $10; exit}')"
fi
[ -n "$KEY_ID" ] || { echo "--key-id ou --generate-key requis"; exit 1; }
gpg --list-secret-keys "$KEY_ID" >/dev/null 2>&1 \
    || { echo "Clé SECRÈTE $KEY_ID introuvable dans $GNUPGHOME : reprepro ne pourra pas signer."; exit 1; }

mkdir -p "$REPO_DIR/conf"
cat > "$REPO_DIR/conf/distributions" <<CONF
Origin: CICADA
Label: CICADA
Codename: stable
Architectures: amd64
Components: main
Description: Paquets de CICADA (RNF)
SignWith: $KEY_ID
CONF
gpg --armor --export "$KEY_ID" > "$REPO_DIR/cicada-repo-key.gpg"
reprepro -b "$REPO_DIR" export stable
echo "Dépôt prêt : $REPO_DIR (clé $KEY_ID, publique dans cicada-repo-key.gpg)"
cat <<VHOST

Vhost Apache proposé (/etc/apache2/sites-available/cicada-apt.conf) :
  <VirtualHost *:80>
      ServerName apt.cicada.reserves-naturelles.org
      DocumentRoot $REPO_DIR
      <Directory $REPO_DIR>
          Options Indexes FollowSymLinks
          Require all granted
      </Directory>
      # Configuration et base internes de reprepro : jamais publiques
      <DirectoryMatch "^$REPO_DIR/(conf|db)">
          Require all denied
      </DirectoryMatch>
  </VirtualHost>
VHOST
