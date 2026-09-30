# PostgreSQL 17 + PostGIS installés sur l'hôte, comme le décrit l'étape 3 de
# docs/INSTALLATION_GUIDE.md (dépôt officiel apt.postgresql.org).
# shellcheck shell=bash
# Sourcé par un scénario (fonctions record/check disponibles).

install_host_postgres() {
    if ! command -v lsb_release >/dev/null 2>&1; then
        # Le guide utilise $(lsb_release -cs), absent des images Debian minimales.
        record INFO "Guide : lsb_release absent, la commande d'ajout du dépôt PGDG échoue telle quelle"
    fi
    . /etc/os-release
    apt-get install -y -qq curl ca-certificates gnupg >/dev/null
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        | gpg --dearmor --yes -o /usr/share/keyrings/postgresql-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] http://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list
    apt-get update -qq
    apt-get install -y -qq postgresql-17 postgresql-17-postgis-3 >/dev/null || return 1
    systemctl enable --now postgresql >/dev/null
    wait_for 30 sudo -u postgres psql -Atc 'select 1'
}

# psql en super-utilisateur postgres
pg() { sudo -u postgres psql -v ON_ERROR_STOP=1 -Atc "$1"; }
