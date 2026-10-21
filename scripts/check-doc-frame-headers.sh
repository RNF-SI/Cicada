#!/bin/sh
# #744 — vérifie que l'Apache du conteneur frontend laisse la documentation
# afficher Swagger UI dans son iframe (X-Frame-Options SAMEORIGIN sous /aide/)
# sans relâcher la protection de l'application (DENY ailleurs).
#
# Usage : scripts/check-doc-frame-headers.sh <dossier du site MkDocs construit>
set -eu

SITE=$(cd "$1" && pwd)
CONF=$(cd "$(dirname "$0")/.." && pwd)/frontend/docker/apache/httpd.conf
PORT=${PORT:-18099}
NAME=cicada-doc-headers

# Une page Swagger réelle du site construit (iframe générée par swagger-ui-tag).
IFRAME=$(cd "$SITE" && find api -name 'swagger-*.html' | head -n 1)
[ -n "$IFRAME" ] || { echo "Aucune page swagger-*.html dans $SITE/api"; exit 1; }

HTDOCS=$(mktemp -d)
mkdir -p "$HTDOCS/aide" && cp -r "$SITE"/. "$HTDOCS/aide/"
echo '<html></html>' > "$HTDOCS/index.html"

docker rm -f "$NAME" >/dev/null 2>&1 || true
docker run -d --name "$NAME" --add-host web:127.0.0.1 -p "$PORT:80" \
  -v "$CONF:/usr/local/apache2/conf/httpd.conf:ro" \
  -v "$HTDOCS:/usr/local/apache2/htdocs:ro" httpd:2.4-alpine >/dev/null
trap 'docker rm -f "$NAME" >/dev/null 2>&1; rm -rf "$HTDOCS"' EXIT

for _ in 1 2 3 4 5 6 7 8 9 10; do
  curl -s -o /dev/null "http://localhost:$PORT/" && break
  sleep 1
done

entete() {
  curl -sI "http://localhost:$PORT$1" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-frame-options"{print $2}'
}

ECHEC=0
verifie() {
  obtenu=$(entete "$1")
  if [ "$obtenu" = "$2" ]; then
    echo "OK   $1 -> $obtenu"
  else
    echo "KO   $1 -> '${obtenu}' (attendu $2)"
    ECHEC=1
  fi
}

verifie "/aide/$IFRAME" SAMEORIGIN
verifie "/aide/" SAMEORIGIN
verifie "/accueil" DENY
exit $ECHEC
