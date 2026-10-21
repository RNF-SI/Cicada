#!/bin/bash
# Vérifie le code Python embarqué dans le paquet .deb avant de le construire.
#
# 1. pyflakes : variable non définie, import manquant… Python ne les signale
#    qu'à l'exécution de la ligne, c'est-à-dire chez le client. C'est ce qui a
#    cassé toutes les installations neuves de 0.1.56 à 0.1.58.
# 2. pytest : déroule l'installateur web de bout en bout pour chaque
#    configuration du formulaire (tests/test_install_service.py).
#
# Appelé par build-deb.sh et par la CI. Outils pris dans $CHECK_PYTHON s'il
# est fourni, sinon installés dans un venv temporaire.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PY="${CHECK_PYTHON:-}"
if [ -z "$PY" ]; then
    VENV="$(mktemp -d)"
    trap 'rm -rf "$VENV"' EXIT
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --disable-pip-version-check \
        pyflakes pytest -r debian/usr/share/cicada/install/requirements.txt
    PY="$VENV/bin/python"
fi

echo "==> pyflakes (code Python du paquet)"
"$PY" -m pyflakes \
    debian/usr/share/cicada/install/*.py \
    debian/usr/bin/cicada-updater \
    debian/usr/bin/cicada-heartbeat

echo "==> pytest (installateur web)"
"$PY" -m pytest -q -p no:cacheprovider tests/
