#!/bin/bash
# publish.sh — Ajoute un .deb de CICADA au dépôt APT (distribution stable)
#   sudo ./publish.sh cicada_0.1.50_amd64.deb [--dir /var/www/repos/cicada]
# reprepro garde une seule version par paquet et par distribution : publier
# 0.1.50 remplace 0.1.49 (apt install cicada=0.1.49 n'est alors plus possible).
set -euo pipefail
DEB="$1"; shift || true
REPO_DIR="/var/www/repos/cicada"
[ "${1:-}" = "--dir" ] && REPO_DIR="$2"
[ -f "$DEB" ] || { echo "Fichier introuvable : $DEB"; exit 1; }
export GNUPGHOME="${GNUPGHOME:-/root/.gnupg}"
export GPG_TTY="$(tty 2>/dev/null || true)"
reprepro -b "$REPO_DIR" includedeb stable "$DEB"
reprepro -b "$REPO_DIR" list stable
