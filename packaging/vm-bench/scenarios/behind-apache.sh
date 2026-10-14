# DESCRIPTION: Apache de l'hôte devant CICADA, avec un « GeoNature » sur :8000 (vhost de l'ancien guide vs guide actuel, #231)
# shellcheck shell=bash
# Sourcé par guest/run-scenario.sh.
#
# Serveur mutualisé typique : Apache sert déjà d'autres applications et un
# gunicorn (GeoNature) écoute sur 127.0.0.1:8000. On installe CICADA derrière
# Apache avec les deux vhosts documentés :
#   - celui de l'ancien guide (ProxyPass /api → :8000) : doit échouer, c'est #231 ;
#   - celui du guide actuel (tout vers le port du frontend) : doit fonctionner.

. "$BENCH_DIR/scenarios/fresh-dockerdb.sh"

scenario_prereqs() {
    apt-get install -y -qq apache2 >/dev/null || return 1
    a2enmod -q proxy proxy_http headers >/dev/null
    a2dissite -q 000-default >/dev/null

    # Faux GeoNature : répond 404 à tout, avec l'en-tête X-Request-ID de GeoNature
    cat > /usr/local/bin/faux-geonature.py <<'EOF'
from http.server import BaseHTTPRequestHandler, HTTPServer
class H(BaseHTTPRequestHandler):
    def _r(self):
        self.send_response(404); self.send_header('X-Request-ID', 'geonature')
        self.send_header('Content-Type', 'text/html'); self.end_headers()
        self.wfile.write(b'<h1>Not Found</h1>GeoNature')
    do_GET = do_POST = _r
    def log_message(self, *a): pass
HTTPServer(('127.0.0.1', 8000), H).serve_forever()
EOF
    systemd-run --quiet --unit=faux-geonature python3 /usr/local/bin/faux-geonature.py
    systemctl reload apache2
    record INFO "Apache $(apache2 -v | awk -F/ 'NR==1{print $2}' | cut -d' ' -f1) + faux GeoNature sur 127.0.0.1:8000"
}

# Vhost HTTP sur le domaine CICADA (résolu vers la VM par /etc/hosts)
vhost() {
    local nom="$1" regle_api="$2"
    cat > /etc/apache2/sites-available/cicada.conf <<EOF
<VirtualHost *:80>
    ServerName $DOMAIN
    ProxyPreserveHost On
    ProxyRequests Off
$regle_api
    ProxyPass / http://127.0.0.1:$FRONTEND_PORT/
    ProxyPassReverse / http://127.0.0.1:$FRONTEND_PORT/
</VirtualHost>
EOF
    a2ensite -q cicada >/dev/null
    apachectl configtest >/dev/null 2>&1 || { record FAIL "Vhost « $nom » valide (apachectl configtest)"; return 1; }
    systemctl reload apache2
}

# Connexion du super-admin à travers Apache, sur http://$DOMAIN/
login_via_apache() {
    curl -s -o /dev/null -w '%{http_code}' --max-time 20 --resolve "$DOMAIN:80:127.0.0.1" \
        -H 'Content-Type: application/json' \
        -d "{\"username\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}" "http://$DOMAIN/api/auth/login/"
}
api_est_cicada() {
    curl -s -D - -o /dev/null --max-time 10 --resolve "$DOMAIN:80:127.0.0.1" "http://$DOMAIN/api/health/" \
        | grep -qi '^x-correlation-id'
}

scenario_checks() {
    step "Vhost de l'ancien guide (ProxyPass /api → :8000)"
    vhost "ancien guide" "    ProxyPass /api http://127.0.0.1:8000/api
    ProxyPassReverse /api http://127.0.0.1:8000/api"
    local code; code="$(login_via_apache)"
    if [ "$code" = 200 ]; then
        record INFO "Ancien vhost : connexion réussie (bug #231 non reproduit)"
    else
        record INFO "Ancien vhost : connexion en échec (HTTP $code) — bug #231 reproduit"
    fi

    step "Vhost du guide actuel (tout vers :$FRONTEND_PORT)"
    vhost "guide actuel" ""
    check "Frontend servi par Apache sur http://$DOMAIN/" \
        test "$(curl -s -o /dev/null -w '%{http_code}' --resolve "$DOMAIN:80:127.0.0.1" "http://$DOMAIN/")" = 200
    check "/api/ servi par CICADA et non par GeoNature (X-Correlation-ID)" api_est_cicada
    check "Connexion du super-admin à travers Apache" test "$(login_via_apache)" = 200
}
