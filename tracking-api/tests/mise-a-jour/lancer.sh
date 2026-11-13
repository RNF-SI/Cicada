#!/bin/bash
# Banc de la mise à jour de l'API de suivi (mettre-a-jour.sh), hors CI : Docker seul, ~3 min.
#   tracking-api/tests/mise-a-jour/lancer.sh [DEPART] [CIBLE]     (défaut : v0.1.50 v0.1.72)
# Deux conteneurs : la base (PostgreSQL 17, « autre serveur ») et le serveur de suivi (Python 3.13,
# comme la production), reconstitué tel qu'on l'a trouvé le 13/11/2026 — voir scenario.sh.
# Le script testé est celui de la copie de travail ; les versions, des étiquettes du dépôt local.
set -euo pipefail
ICI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RACINE="$(git -C "$ICI" rev-parse --show-toplevel)"
DEPART="${1:-v0.1.50}"
CIBLE="${2:-v0.1.72}"
N="cicada-banc-suivi-$$"
nettoyer() { docker rm -f "$N-base" "$N-suivi" >/dev/null 2>&1 || true; docker network rm "$N" >/dev/null 2>&1 || true; }
trap nettoyer EXIT
docker network create "$N" >/dev/null
docker run -d --name "$N-base" --network "$N" --network-alias base \
    -e POSTGRES_PASSWORD=admin postgres:17 >/dev/null
sleep 3; for _ in $(seq 60); do docker exec "$N-base" pg_isready -q -U postgres && break; sleep 1; done
docker run --name "$N-suivi" --network "$N" -v "$RACINE:/src:ro" python:3.13-slim \
    bash /src/tracking-api/tests/mise-a-jour/scenario.sh "$DEPART" "$CIBLE"
