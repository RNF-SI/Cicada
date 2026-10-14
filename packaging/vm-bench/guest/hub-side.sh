#!/bin/bash
# Exécuté sur la VM hub au début d'un scénario : déploiement selon
# docs/DEPLOIEMENT_HUB.md (étapes 2, 3, Apache) puis enrôlement de l'instance.
# Écrit les jetons délivrés dans $BENCH_DIR/hub-jetons (repris par bench.sh).
set -uo pipefail
VERSION="$1"; INSTANCE_ID="$2"; LIBELLE="$3"; INSTANCE_URL="$4"
BENCH_DIR="${BENCH_DIR:-/home/ubuntu/bench}"
. "$BENCH_DIR/guest/lib.sh"
: > "$RESULTS"
IP="$(hostname -I | awk '{print $1}')"
cd /opt/cicada-hub || exit 1
COMPOSE=(docker compose -f docker-compose.hub.prod.yml --env-file .env.hub.prod)

step "Hub : déploiement ($IP, cicada-hub:$VERSION)"
# 2. Configurer (à partir de l'exemple du dépôt, comme le guide). localhost et
# 127.0.0.1 : healthcheck et vérification ; les images <= 0.1.49 ne les
# admettent pas d'office (corrigé dans hub/config/settings.py).
cp .env.hub.prod.example .env.hub.prod
chmod 600 .env.hub.prod
sed -i -e "s|^CICADA_VERSION=.*|CICADA_VERSION=$VERSION|" \
       -e "s|^SECRET_KEY=.*|SECRET_KEY=$(head -c 48 /dev/urandom | base64 | tr -d '/+=')|" \
       -e "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=$IP,localhost,127.0.0.1|" \
       -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(head -c 24 /dev/urandom | base64 | tr -d '/+=')|" \
       .env.hub.prod

# 3. Démarrer
"${COMPOSE[@]}" up -d 2>&1 | tail -3
if wait_for 600 curl -sf http://127.0.0.1:8002/api/health/; then
    record PASS "Hub : démarré (/api/health/)" "$(curl -s http://127.0.0.1:8002/api/health/)"
else
    record FAIL "Hub : démarré (/api/health/)" "$("${COMPOSE[@]}" logs --tail 5 hub 2>&1 | tail -3)"
    exit 1
fi

# Apache : vhost du guide, en HTTP (pas de certificat dans le banc)
cat > /etc/apache2/sites-available/cicada-hub.conf <<VHOST
<VirtualHost *:80>
    ServerName $IP
    ProxyPreserveHost On
    ProxyPass        / http://127.0.0.1:8002/
    ProxyPassReverse / http://127.0.0.1:8002/
    LimitRequestBody 104857600
    ProxyTimeout 300
</VirtualHost>
VHOST
a2ensite -q cicada-hub >/dev/null && systemctl reload apache2
check "Hub : servi par Apache sur http://$IP/" curl -sf "http://$IP/api/health/"

# Enrôler l'instance : deux jetons, affichés une seule fois
out="$("${COMPOSE[@]}" exec -T hub python manage.py enroler_instance "$INSTANCE_ID" \
        --libelle "$LIBELLE" --url "$INSTANCE_URL" 2>&1)"
echo "$out" | sed 's/^/   /'
# Lignes « dépôt    : <jeton> » et « lecture  : <jeton> »
# (libellé accentué « dépôt » : grep -E, pas awk, qui ne sait pas l'UTF-8 partout)
depot="$(echo "$out" | sed 's/\x1b\[[0-9;]*m//g' | grep -E '^[[:space:]]*(dépôt|depot)[[:space:]]*:' | head -1 | awk '{print $NF}')"
lecture="$(echo "$out" | sed 's/\x1b\[[0-9;]*m//g' | grep -E '^[[:space:]]*lecture[[:space:]]*:' | head -1 | awk '{print $NF}')"
if [ -n "$depot" ] && [ -n "$lecture" ]; then
    record PASS "Hub : instance « $INSTANCE_ID » enrôlée (2 jetons délivrés)"
    printf 'HUB_URL=http://%s\nHUB_PUSH=%s\nHUB_READ=%s\n' "$IP" "$depot" "$lecture" > "$BENCH_DIR/hub-jetons"
else
    record FAIL "Hub : instance « $INSTANCE_ID » enrôlée" "$(echo "$out" | tail -2)"
fi
