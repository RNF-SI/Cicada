#!/bin/bash
# Dans le conteneur « serveur de suivi » du banc (lancé par lancer.sh). Reconstitue le serveur de
# production tel qu'on l'a trouvé le 13/11/2026, puis rejoue la mise à jour cas par cas :
#   clone /home/tracking/Cicada à « tracking », posé sur l'étiquette de départ ; tracking-api/ à www-data ;
#   base sur un autre serveur ; tables créées par postgres, le compte de l'API n'ayant que lecture/écriture.
set -uo pipefail
DEPART="$1"; CIBLE="$2"; VERSION="${CIBLE#v}"
R=/home/tracking/Cicada; D=$R/tracking-api
DEPOT=/var/www/repos/cicada; INDEX=$DEPOT/dists/stable/main/binary-amd64/Packages
MAJ=(bash /root/mettre-a-jour.sh "$CIBLE" --depot-url http://depot.invalide)
ECHECS=0
ok() { echo "  ✓ $*"; }
ko() { echo "  ✗ $*"; ECHECS=$((ECHECS + 1)); }
verifie() { local libelle="$1"; shift; if "$@"; then ok "$libelle"; else ko "$libelle"; fi; }
cas() { printf '\n######## %s\n' "$*"; }
pg() { PGPASSWORD=admin psql -h base -U postgres -v ON_ERROR_STOP=1 -Atq "$@"; }
tete() { git -c safe.directory='*' -C "$R" describe --tags --exact-match 2>/dev/null; }
annonce() { sed -n 's/^LATEST_VERSION=//p' "$D/.env"; }
drf() { "$D/venv/bin/pip" show djangorestframework 2>/dev/null | sed -n 's/^Version: //p'; }
repond() { [ "$(curl -s -o /dev/null -w '%{http_code}' -H 'Host: tracking.test' http://127.0.0.1:8000/admin/login/)" = 200 ]; }
publier() { mkdir -p "$(dirname "$INDEX")"; printf 'Package: cicada\nVersion: %s\nArchitecture: amd64\n\n' "$1" > "$INDEX"; }
heartbeat() {
    curl -s -X POST -H 'Host: tracking.test' -H 'Content-Type: application/json' \
        -H "X-Instance-Token: $JETON" -d '{"version":"0.1.69"}' http://127.0.0.1:8000/api/instances/heartbeat/
}
instance_reconnue() { heartbeat | grep -q '"status":"ok"'; }
annoncee_a_l_instance() { heartbeat | grep -q "\"latest_version\":\"$VERSION\""; }

echo "Préparation du serveur ($DEPART, base distante, tables à postgres)…"
apt-get update -qq && apt-get install -y -qq git sudo curl postgresql-client >/dev/null 2>&1
git config --system --add safe.directory /src
git config --system --add safe.directory /src/.git
install -m 0755 /src/tracking-api/tests/mise-a-jour/systemctl /usr/local/bin/systemctl
cp /src/tracking-api/mettre-a-jour.sh /root/mettre-a-jour.sh     # comme le curl depuis l'étiquette
useradd -m tracking
chmod 755 /home/tracking     # comme en production : www-data traverse le dossier personnel
mkdir -p /var/www
runuser -u tracking -- git clone -q --no-checkout /src "$R"
runuser -u tracking -- git -C "$R" checkout -q "$DEPART"
python3 -m venv "$D/venv"
"$D/venv/bin/pip" install -q --disable-pip-version-check -r "$D/requirements.txt" gunicorn 2>&1 | grep -v WARNING

pg -c "CREATE ROLE tracking_user LOGIN PASSWORD 'suivi'" -c "CREATE DATABASE tracking_cicada"
ecrire_env() {
    cat > "$D/.env" <<ENV
DEBUG=False
SECRET_KEY=$2
ALLOWED_HOSTS=tracking.test,localhost
DB_NAME=tracking_cicada
DB_USER=$1
DB_PASSWORD=$([ "$1" = postgres ] && echo admin || echo suivi)
DB_HOST=base
DB_PORT=5432
LATEST_VERSION=0.1.69
ENV
}
# Installation d'origine : migrations lancées avec le compte postgres, droits accordés ensuite.
ecrire_env postgres "cle-du-banc-$(head -c 24 /dev/urandom | base64 | tr -d '/+=')"
(cd "$D" && venv/bin/python manage.py migrate -v 0 && venv/bin/python manage.py collectstatic --noinput -v 0)
pg -d tracking_cicada -c "GRANT USAGE, CREATE ON SCHEMA public TO tracking_user" \
    -c "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tracking_user" \
    -c "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tracking_user"
CLE="$(sed -n 's/^SECRET_KEY=//p' "$D/.env")"
ecrire_env tracking_user "$CLE"
chown -R www-data:www-data "$D"
systemctl restart cicada-tracking-api
JETON="$(python3 -c 'import uuid;print(uuid.uuid4())')"
curl -s -o /dev/null -H 'Host: tracking.test' -H 'Content-Type: application/json' \
    -d "{\"token\":\"$JETON\",\"version\":\"0.1.69\"}" http://127.0.0.1:8000/api/instances/register/
verifie "serveur reconstitué en $DEPART" test "$(tete)" = "$DEPART"
verifie "service qui répond, une instance enregistrée" instance_reconnue

cas "1. --verifier : tables à postgres signalées, rien ne change"
"${MAJ[@]}" --verifier; code=$?
verifie "sortie en échec" test "$code" != 0
verifie "tables de postgres signalées et SQL écrit" grep -q "OWNER TO" /root/cicada-tracking-droits.sql
verifie "code toujours en $DEPART" test "$(tete)" = "$DEPART"

cas "2. Mise à jour lancée sans corriger les droits : arrêt avant toute modification"
"${MAJ[@]}"; code=$?
verifie "sortie en échec" test "$code" != 0
verifie "code toujours en $DEPART" test "$(tete)" = "$DEPART"
verifie "aucune sauvegarde (rien n'a commencé)" test ! -d /var/backups/cicada-tracking
verifie "annonce inchangée (0.1.69)" test "$(annonce)" = 0.1.69
verifie "service toujours debout" repond

cas "3. SQL fourni lancé sur le serveur de la base (en postgres)"
pg -d tracking_cicada -f /root/cicada-tracking-droits.sql
verifie "toutes les tables à tracking_user" \
    test "$(pg -d tracking_cicada -c "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner <> 'tracking_user'")" = 0

cas "4. .env refusé par la nouvelle version : retour automatique au code de départ"
DRF_AVANT="$(drf)"
echo "EMAIL_PORT=pas-un-nombre" >> "$D/.env"
"${MAJ[@]}"; code=$?
verifie "sortie en échec" test "$code" != 0
verifie "code remis en $DEPART" test "$(tete)" = "$DEPART"
verifie "dépendances de départ remises (DRF $DRF_AVANT)" test "$(drf)" = "$DRF_AVANT"
verifie "annonce inchangée (0.1.69)" test "$(annonce)" = 0.1.69
verifie "service toujours debout, instance reconnue" instance_reconnue
sed -i '/^EMAIL_PORT=/d' "$D/.env"

cas "5. Paquet pas encore publié sur le dépôt APT : code à jour, version non annoncée"
publier 0.1.69
"${MAJ[@]}"; code=$?
verifie "sortie 3 (à annoncer après publication)" test "$code" = 3
verifie "code en $CIBLE" test "$(tete)" = "$CIBLE"
verifie "annonce inchangée (0.1.69)" test "$(annonce)" = 0.1.69
verifie "migrations appliquées" bash -c "cd $D && sudo -u www-data venv/bin/python manage.py migrate --check >/dev/null"
verifie "l'instance s'authentifie toujours (jeton en empreinte)" instance_reconnue
verifie "sauvegarde 0600 dans un dossier 0700" \
    bash -c "[ \"\$(stat -c %a /var/backups/cicada-tracking)\" = 700 ] && [ \"\$(stat -c %a /var/backups/cicada-tracking/*.json | sort -u)\" = 600 ]"

cas "6. Paquet publié : relance, la version est annoncée"
publier "$VERSION"
"${MAJ[@]}"; code=$?
verifie "sortie 0" test "$code" = 0
verifie "LATEST_VERSION=$VERSION" test "$(annonce)" = "$VERSION"
verifie "heartbeat : $VERSION annoncée à l'instance" annoncee_a_l_instance
verifie "fichiers de l'API rendus à www-data (hors .env)" \
    test -z "$(find "$D" \( -path "$D/venv" -o -path "$D/static" \) -prune -o -user root ! -name .env -print)"
verifie "une sauvegarde par passage (3)" test "$(ls /var/backups/cicada-tracking/*.json | wc -l)" = 3

cas "7. Version plus ancienne refusée"
"${MAJ[@]/$CIBLE/$DEPART}"; code=$?
verifie "sortie en échec, code toujours en $CIBLE" bash -c "[ $code != 0 ] && [ '$(tete)' = '$CIBLE' ]"

echo
if [ "$ECHECS" = 0 ]; then echo "BANC MISE À JOUR SUIVI : tout passe"; else echo "BANC MISE À JOUR SUIVI : $ECHECS échec(s)"; fi
exit "$ECHECS"
