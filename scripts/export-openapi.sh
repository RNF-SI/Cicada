#!/usr/bin/env bash
# Exporte le schéma OpenAPI de l'API (drf-spectacular) vers la documentation
# statique, qui l'embarque dans « API › Référence des endpoints ».
#
#   scripts/export-openapi.sh            # via docker compose (stack de dev)
#   scripts/export-openapi.sh --local    # avec un Python local (backend/ sur le PYTHONPATH)
#
# À relancer après tout changement d'endpoint, de serializer ou de permission,
# puis committer documentation/docs/api/openapi.json : le site de documentation
# est construit sans Django, il ne peut pas générer le schéma lui-même.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/documentation/docs/api/openapi.json"

if [[ "${1:-}" == "--local" ]]; then
  (cd "$ROOT/backend" && python manage.py spectacular --format openapi-json --validate --file "$OUT")
else
  # --entrypoint "" : l'entrypoint de l'image attend PostgreSQL, inutile ici (le
  # schéma se calcule sans base). ./backend est monté sur /app : le fichier
  # écrit dans le conteneur atterrit directement dans le dépôt.
  docker compose -f "$ROOT/docker-compose.yml" run --rm --no-deps -T --entrypoint "" web \
    python manage.py spectacular --format openapi-json --file /app/_openapi.json
  # Le fichier appartient à root (écrit par le conteneur) : on le recopie plutôt que de le déplacer.
  cat "$ROOT/backend/_openapi.json" > "$OUT"
  rm -f "$ROOT/backend/_openapi.json"
fi

python3 - "$OUT" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
# Compact (1,2 Mo au lieu de 4) : le fichier est servi tel quel par la page de référence.
json.dump(d, open(p, "w"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
print(f"{p}: {len(d.get('paths', {}))} chemins, OpenAPI {d.get('openapi')}")
PY
