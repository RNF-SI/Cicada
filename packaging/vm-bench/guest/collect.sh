#!/bin/bash
# Diagnostic rapatrié sur l'hôte après chaque scénario (réussi ou non).
BENCH_DIR="${BENCH_DIR:-/home/ubuntu/bench}"
section() { echo; echo "===== $* ====="; }

section "systemd"
systemctl is-system-running
systemctl --failed --no-pager
for u in cicada-installer.service cicada-heartbeat.timer cicada-updater.path; do
    echo "$u : $(systemctl is-enabled "$u" 2>&1) / $(systemctl is-active "$u" 2>&1)"
done

section "Réponse de l'installateur"
cat "$BENCH_DIR/install-response.json" 2>/dev/null; echo
section "install_status.json"
cat /var/lib/cicada/install_status.json 2>/dev/null; echo

section ".env (secrets masqués)"
sed -E 's/^((SECRET_KEY|POSTGRES_PASSWORD|REDIS_PASSWORD|EMAIL_HOST_PASSWORD|INSTANCE_TOKEN|CICADA_HUB_[A-Z_]*TOKEN)=).+/\1***/' /var/lib/cicada/.env 2>/dev/null

section "docker ps -a"
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>&1
section "réseaux docker"
docker network inspect cicada_network --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>&1

section "logs web (120 dernières lignes)"
docker logs --tail 120 cicada_prod_web 2>&1
section "logs db (40)"
docker logs --tail 40 cicada_prod_db 2>&1

section "journal cicada-installer"
journalctl -u cicada-installer --no-pager 2>&1 | tail -40
section "journal cicada-heartbeat"
journalctl -u cicada-heartbeat --no-pager 2>&1 | tail -20

section "Appels reçus par la fausse API de suivi"
cat "$BENCH_DIR/fake-tracking.log" 2>/dev/null

if command -v psql >/dev/null 2>&1; then
    section "PostgreSQL hôte"
    ss -ltnp | grep 5432
    sudo -u postgres psql -Atc "select datname from pg_database" 2>&1
    tail -30 /var/log/postgresql/postgresql-*-main.log 2>/dev/null
fi

section "disque"
df -h / /var/lib/docker 2>/dev/null
