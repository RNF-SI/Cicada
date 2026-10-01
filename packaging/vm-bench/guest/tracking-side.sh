#!/bin/bash
# Exécuté sur la VM « tracking » au début d'un scénario : déploie l'API de suivi
# selon tracking-api/INSTALLATION.md et le dépôt APT avec packaging/apt-repo/,
# puis publie les paquets fournis. Écrit l'adresse de la VM dans tracking-pret.
#   tracking-side.sh LATEST_VERSION paquet.deb…
set -uo pipefail
LATEST="$1"; shift
BENCH_DIR="${BENCH_DIR:-/home/ubuntu/bench}"
. "$BENCH_DIR/guest/lib.sh"
: > "$RESULTS"
IP="$(hostname -I | awk '{print $1}')"
grep -q 'cicada.bench' /etc/hosts || echo "127.0.0.1 tracking.cicada.bench apt.cicada.bench" >> /etc/hosts
pgx() { runuser -u postgres -- psql -v ON_ERROR_STOP=1 -Atq "$@"; }

step "Tracking : API de suivi (tracking-api/INSTALLATION.md)"
rm -rf /opt/tracking-api && cp -r "$BENCH_DIR/tracking-api" /opt/tracking-api
cd /opt/tracking-api
python3 -m venv venv
venv/bin/pip install -q -r requirements.txt gunicorn 2>&1 | tail -1
DBPASS="$(head -c 18 /dev/urandom | base64 | tr -d '/+=')"
pgx -c "CREATE ROLE tracking_user LOGIN PASSWORD '$DBPASS'" -c "CREATE DATABASE tracking OWNER tracking_user"
cat > .env <<ENV
DEBUG=False
SECRET_KEY=$(head -c 48 /dev/urandom | base64 | tr -d '/+=')
ALLOWED_HOSTS=tracking.cicada.bench,localhost
DB_NAME=tracking
DB_USER=tracking_user
DB_PASSWORD=$DBPASS
DB_HOST=localhost
DB_PORT=5432
LATEST_VERSION=$LATEST
ENV
if out="$(venv/bin/python manage.py migrate --noinput 2>&1)"; then
    record PASS "Tracking : migrations (installation neuve)"
else
    record FAIL "Tracking : migrations (installation neuve)" "$(echo "$out" | tail -2)"
fi
venv/bin/python manage.py collectstatic --noinput -v0
chown -R www-data:www-data /opt/tracking-api
cat > /etc/systemd/system/cicada-tracking-api.service <<'UNIT'
[Unit]
Description=CICADA Tracking API
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/tracking-api
Environment="PATH=/opt/tracking-api/venv/bin"
ExecStart=/opt/tracking-api/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 tracking.wsgi:application

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload && systemctl enable --now cicada-tracking-api >/dev/null 2>&1
cat > /etc/apache2/sites-available/cicada-tracking-api.conf <<'VHOST'
<VirtualHost *:80>
    ServerName tracking.cicada.bench
    ProxyPreserveHost On
    ProxyPass /static !
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
    Alias /static /opt/tracking-api/static
    <Directory /opt/tracking-api/static>
        Require all granted
    </Directory>
</VirtualHost>
VHOST
a2ensite -q cicada-tracking-api >/dev/null
wait_for 30 curl -s -o /dev/null http://127.0.0.1:8000/admin/login/
TOK="$(python3 -c 'import uuid;print(uuid.uuid4())')"
code="$(curl -s -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' \
    -d "{\"token\":\"$TOK\",\"version\":\"0.0.0\"}" http://localhost:8000/api/instances/register/)"
check "Tracking : API répond (register d'essai)" test "$code" = 201
pgx -d tracking -c "DELETE FROM tracking_instances WHERE token='$TOK'"

step "Tracking : dépôt APT (packaging/apt-repo)"
export GNUPGHOME=/root/.gnupg
if out="$(bash "$BENCH_DIR/apt-repo/init-repo.sh" --dir /var/www/repos/cicada --generate-key "CICADA banc <banc@cicada.bench>" 2>&1)"; then
    record PASS "Dépôt APT initialisé et signé (init-repo.sh)"
else
    record FAIL "Dépôt APT initialisé et signé (init-repo.sh)" "$(echo "$out" | tail -2)"
fi
for deb in "$@"; do
    if out="$(bash "$BENCH_DIR/apt-repo/publish.sh" "$deb" --dir /var/www/repos/cicada 2>&1)"; then
        record PASS "Publié dans le dépôt : $(basename "$deb")"
    else
        record FAIL "Publié dans le dépôt : $(basename "$deb")" "$(echo "$out" | tail -2)"
    fi
done
# Vhost proposé par init-repo.sh
cat > /etc/apache2/sites-available/cicada-apt.conf <<'VHOST'
<VirtualHost *:80>
    ServerName apt.cicada.bench
    DocumentRoot /var/www/repos/cicada
    <Directory /var/www/repos/cicada>
        Options Indexes FollowSymLinks
        Require all granted
    </Directory>
    <DirectoryMatch "^/var/www/repos/cicada/(conf|db)">
        Require all denied
    </DirectoryMatch>
</VirtualHost>
VHOST
a2ensite -q cicada-apt >/dev/null && systemctl reload apache2
check "Dépôt servi : Release signé" curl -sf http://apt.cicada.bench/dists/stable/InRelease -o /dev/null
check "Dépôt : conf/ non publique" test "$(curl -s -o /dev/null -w '%{http_code}' http://apt.cicada.bench/conf/distributions)" = 403
echo "$IP" > "$BENCH_DIR/tracking-pret"
