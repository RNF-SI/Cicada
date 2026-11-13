#!/bin/bash
# mettre-a-jour.sh — Met l'API de suivi à la version vX.Y.Z de CICADA et l'annonce aux instances.
#   sudo bash mettre-a-jour.sh vX.Y.Z              mise à jour complète
#   sudo bash mettre-a-jour.sh vX.Y.Z --verifier   contrôles seuls : rien ne change
# Options : --service NOM (défaut cicada-tracking-api), --dossier DIR (défaut : lu dans le
# service), --depot DIR (dépôt APT local, défaut /var/www/repos/cicada), --depot-url URL.
#
# Tout ce qui a bloqué la mise à jour 0.1.50 → 0.1.72 (13/11/2026) est contrôlé AVANT de toucher
# à quoi que ce soit :
#   - clone posé sur une étiquette (git pull impossible)          → fetch de l'étiquette + checkout ;
#   - dépôt et dossier de l'API à deux propriétaires              → git en root, le reste sous le
#     (git refuse : « propriétaire douteux »)                        compte propriétaire du dossier ;
#   - base sur un autre serveur (pas de pg_dump ici)              → sauvegarde par l'application ;
#   - tables créées par postgres (migrations refusées)            → arrêt, SQL à lancer fourni ;
#   - clé secrète par défaut (la nouvelle version ne démarre pas) → clé tirée au sort ;
#   - version annoncée avant d'être publiée (le bouton échoue)    → annoncée seulement si publiée.
# En cas d'échec avant toute migration, le code et les dépendances de départ sont remis et le
# service n'est pas redémarré. Relancer le script est sans risque.
set -euo pipefail

SERVICE=cicada-tracking-api
DIR=""
DEPOT=/var/www/repos/cicada
DEPOT_URL=https://apt.cicada.reserves-naturelles.org
CIBLE=""
VERIFIER=0
SAUV_DIR=/var/backups/cicada-tracking
GARDER=5

etape() { printf '\n== %s\n' "$*"; }
info() { printf '   %s\n' "$*"; }
echec() { printf '\nÉCHEC : %s\n' "$*" >&2; exit "${2:-1}"; }

while [ $# -gt 0 ]; do
    case "$1" in
        --verifier) VERIFIER=1 ;;
        --service) SERVICE="$2"; shift ;;
        --dossier) DIR="$2"; shift ;;
        --depot) DEPOT="$2"; shift ;;
        --depot-url) DEPOT_URL="$2"; shift ;;
        -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
        v[0-9]*) CIBLE="$1" ;;
        *) echec "argument inconnu : $1 (aide : --help)" ;;
    esac
    shift
done
[[ "$CIBLE" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || echec "indiquer la version visée, au format vX.Y.Z (ex. v0.1.73)"
VERSION="${CIBLE#v}"
[ "$(id -u)" = 0 ] || echec "à lancer en root (sudo -i)"

# ---------------------------------------------------------------- où est l'API
etape "Emplacement"
DEMARRAGE="$(systemctl show -p ExecStart --value "$SERVICE" 2>/dev/null || true)"
if [ -z "$DIR" ]; then
    EXE="$(sed -n 's/.*path=\([^ ;]*\).*/\1/p' <<<"$DEMARRAGE" | head -1)"
    case "$EXE" in */venv/bin/*) DIR="${EXE%/venv/bin/*}" ;; esac
    [ -n "$DIR" ] || DIR="$(systemctl show -p WorkingDirectory --value "$SERVICE" 2>/dev/null || true)"
fi
[ -n "$DIR" ] && [ -f "$DIR/manage.py" ] && [ -x "$DIR/venv/bin/python" ] \
    || echec "API de suivi introuvable par le service $SERVICE : préciser --dossier"
DIR="$(cd "$DIR" && pwd)"
R="$(git -c safe.directory='*' -C "$DIR" rev-parse --show-toplevel 2>/dev/null)" \
    || echec "$DIR n'est pas dans un clone git du dépôt Cicada"
G=(git -c safe.directory="$R" -c core.fileMode=false -C "$R")
U="$(stat -c %U "$DIR")"
GRP="$(stat -c %G "$DIR")"
BIND="$(sed -n 's/.*argv\[\]=\([^;]*\).*/\1/p' <<<"$DEMARRAGE" | head -1 \
    | sed -n 's/.*\(--bind[= ]\|-b \)\([^ ]*\).*/\2/p')"
BIND="${BIND:-127.0.0.1:8000}"
ANCIEN="$("${G[@]}" rev-parse HEAD)"
ANCIEN_NOM="$("${G[@]}" describe --tags --exact-match 2>/dev/null || "${G[@]}" rev-parse --short HEAD)"
ENV_FILE="$DIR/.env"
[ -f "$ENV_FILE" ] || echec "fichier $ENV_FILE absent"
LATEST_AVANT="$(sed -n 's/^LATEST_VERSION=//p' "$ENV_FILE" | tail -1)"
info "dossier      : $DIR (fichiers à $U, dépôt git $R)"
info "en place     : $ANCIEN_NOM — annonce LATEST_VERSION=${LATEST_AVANT:-vide}"
info "visée        : $CIBLE"

TMPD="$(mktemp -d)"
chown "$U" "$TMPD"
trap 'rm -rf "$TMPD"' EXIT
asu() { sudo -u "$U" -H -- "$@"; }
pipi() { (cd "$DIR" && asu venv/bin/pip install -q --disable-pip-version-check --cache-dir "$TMPD/pip" -r requirements.txt); }
gere() { (cd "$DIR" && asu venv/bin/python manage.py "$@"); }

# État de la base, lu avec le code en place : compte, droits, tables d'un autre propriétaire.
infos_base() {
    (cd "$DIR" && asu venv/bin/python - <<'PY'
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tracking.settings')
import django
django.setup()
from django.conf import settings
from django.db import connection
bd = settings.DATABASES['default']
with connection.cursor() as c:
    c.execute("SELECT current_user, current_database(), has_schema_privilege('public', 'CREATE')")
    compte, base, creer = c.fetchone()
    c.execute("SELECT tablename, tableowner FROM pg_tables WHERE schemaname = 'public'"
              " AND NOT pg_has_role(current_user, tableowner, 'MEMBER') ORDER BY 1")
    autres = c.fetchall()
    try:
        c.execute("SELECT count(*) FROM django_migrations")
        migrations = c.fetchone()[0]
    except Exception:
        migrations = 0
hotes = [h for h in settings.ALLOWED_HOSTS if h and not h.startswith(('.', '*'))]
print(f"COMPTE={compte}")
print(f"BASE={base}")
print(f"HOTE_BASE={bd.get('HOST') or 'ce serveur'}")
print(f"CREER={'oui' if creer else 'non'}")
print(f"MIGRATIONS={migrations}")
print(f"HOTE_HTTP={hotes[0] if hotes else 'localhost'}")
for table, proprietaire in autres:
    print(f"AUTRE={table} ({proprietaire})")
PY
    )
}
lire() { sed -n "s/^$1=//p" <<<"$INFOS"; }

# Index APT publié : celui du dépôt local s'il est sur ce serveur, sinon l'index public.
publication() {
    local index="$DEPOT/dists/stable/main/binary-amd64/Packages" contenu
    if [ -f "$index" ]; then
        contenu="$(cat "$index")"
    elif ! contenu="$(curl -fsS --max-time 20 "$DEPOT_URL/dists/stable/main/binary-amd64/Packages" 2>/dev/null)"; then
        echo inconnue; return
    fi
    awk '/^Package: cicada$/{p=1; next} p && /^Version:/{print $2; exit} /^$/{p=0}' <<<"$contenu"
}

sonder() {
    command -v curl >/dev/null || { systemctl is-active -q "$SERVICE"; return; }
    local code
    if [[ "$BIND" == unix:* ]]; then
        code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 --unix-socket "${BIND#unix:}" \
            -H "Host: $HOTE_HTTP" -H 'X-Forwarded-Proto: https' http://localhost/admin/login/ || true)"
    else
        code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 \
            -H "Host: $HOTE_HTTP" -H 'X-Forwarded-Proto: https' "http://$BIND/admin/login/" || true)"
    fi
    CODE_HTTP="${code:-000}"
    [ "$CODE_HTTP" -ge 200 ] && [ "$CODE_HTTP" -lt 500 ]
}

# Fichiers réécrits par git (en root) : rendus au propriétaire du dossier, sauf .env, venv et static.
rendre_fichiers() {
    [ "$U" = root ] && return
    find "$DIR" \( -path "$DIR/venv" -o -path "$DIR/static" \) -prune -o \
        \( -user root ! -path "$ENV_FILE" \) -exec chown "$U:$GRP" {} +
}

# ---------------------------------------------------------------- contrôles
etape "Contrôles"
A_FAIRE=0
MODIFS="$("${G[@]}" status --porcelain --untracked-files=no)"
if [ -n "$MODIFS" ]; then
    info "✗ fichiers du dépôt modifiés sur ce serveur (ils empêcheraient le changement de version) :"
    sed 's/^/       /' <<<"$MODIFS"
    A_FAIRE=1
else
    info "✓ aucun fichier du dépôt modifié sur ce serveur"
fi

"${G[@]}" fetch --quiet --no-tags origin "+refs/tags/$CIBLE:refs/tags/$CIBLE" 2>"$TMPD/fetch" \
    || echec "étiquette $CIBLE introuvable sur GitHub ($(tail -1 "$TMPD/fetch"))"
info "✓ étiquette $CIBLE récupérée"
if [[ "$ANCIEN_NOM" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] && [ "$ANCIEN_NOM" != "$CIBLE" ] \
   && [ "$(printf '%s\n%s\n' "$ANCIEN_NOM" "$CIBLE" | sort -V | tail -1)" = "$ANCIEN_NOM" ]; then
    echec "$CIBLE est plus ancienne que la version en place ($ANCIEN_NOM) : refusé, la base peut déjà porter des migrations plus récentes"
fi

INFOS="$(infos_base 2>"$TMPD/base")" \
    || echec "base injoignable avec le code en place : $(tail -1 "$TMPD/base")"
COMPTE="$(lire COMPTE)"; BASE="$(lire BASE)"; HOTE_BASE="$(lire HOTE_BASE)"; HOTE_HTTP="$(lire HOTE_HTTP)"
AUTRES="$(lire AUTRE)"
info "✓ base $BASE sur $HOTE_BASE, compte $COMPTE"
if [ -n "$AUTRES" ] || [ "$(lire CREER)" != oui ]; then
    SQL=/root/cicada-tracking-droits.sql
    {
        echo "-- Droits du compte de l'API de suivi sur sa base : à lancer sur le serveur de la base ($HOTE_BASE),"
        echo "-- connecté à la base $BASE en administrateur. psql : sudo -u postgres psql -d $BASE -f $(basename "$SQL")"
        echo "-- DBeaver : coller, sélectionner tout et exécuter. Ne touche à aucune donnée ni à aucune autre base."
        [ "$(lire CREER)" = oui ] || echo "GRANT USAGE, CREATE ON SCHEMA public TO \"$COMPTE\";"
        cat <<SQLDO
DO \$\$
DECLARE t text;
BEGIN
  FOR t IN SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
              AND NOT pg_has_role('$COMPTE', tableowner, 'MEMBER')
  LOOP
    EXECUTE format('ALTER TABLE public.%I OWNER TO %I', t, '$COMPTE');
  END LOOP;
END \$\$;
SQLDO
    } > "$SQL"
    if [ -n "$AUTRES" ]; then
        info "✗ tables qui n'appartiennent pas à $COMPTE (les migrations seraient refusées) :"
        sed 's/^/       /' <<<"$AUTRES"
    fi
    [ "$(lire CREER)" = oui ] || info "✗ $COMPTE ne peut pas créer de table dans le schéma public"
    info "  → SQL à lancer sur $HOTE_BASE, base $BASE : $SQL"
    sed 's/^/       /' "$SQL"
    A_FAIRE=1
else
    info "✓ $COMPTE est propriétaire de toutes ses tables"
fi

CLE="$(sed -n 's/^SECRET_KEY=//p' "$ENV_FILE" | tail -1 | tr -d "\"'")"
CLE_A_POSER=0
if [ -z "$CLE" ] || [[ "$CLE" == django-insecure* ]]; then
    CLE_A_POSER=1
    info "• SECRET_KEY absente ou par défaut : une clé sera tirée au sort (ferme les sessions de l'admin)"
else
    info "✓ SECRET_KEY propre à ce serveur"
fi

PUBLIEE="$(publication)"
case "$PUBLIEE" in
    "$VERSION") info "✓ cicada $VERSION publiée sur le dépôt APT : elle sera annoncée aux instances" ;;
    inconnue) info "• dépôt APT illisible d'ici : $VERSION sera annoncée sans contrôle (vérifier qu'elle est publiée)" ;;
    *) info "• le dépôt APT publie ${PUBLIEE:-rien}, pas $VERSION : le code sera mis à jour, la version ne sera PAS annoncée"
       info "  (publier le paquet avec publish.sh, puis relancer ce script)" ;;
esac

if [ "$VERIFIER" = 1 ]; then
    [ "$A_FAIRE" = 0 ] && { echo; echo "Prêt : la mise à jour vers $CIBLE peut être lancée."; exit 0; }
    echec "à corriger avant la mise à jour (voir ✗ ci-dessus)"
fi
[ "$A_FAIRE" = 0 ] || echec "rien n'a été modifié. Corriger les points ✗ ci-dessus, puis relancer le script"

# ---------------------------------------------------------------- sauvegarde
etape "Sauvegarde (code en place, $ANCIEN_NOM)"
install -d -m 0700 "$SAUV_DIR"
SAUV="$SAUV_DIR/avant-${CIBLE}_depuis-${ANCIEN_NOM}_$(date +%Y%m%d-%H%M%S).json"
(umask 077; gere dumpdata --exclude contenttypes --exclude auth.permission --exclude sessions > "$SAUV") \
    || echec "sauvegarde impossible : rien n'a été modifié"
OBJETS="$("$DIR/venv/bin/python" -c 'import json,sys;print(len(json.load(open(sys.argv[1]))))' "$SAUV")" \
    || echec "sauvegarde illisible ($SAUV) : rien n'a été modifié"
info "$SAUV ($OBJETS objets)"
ls -1t "$SAUV_DIR"/*.json | tail -n +$((GARDER + 1)) | xargs -r rm -f

# ---------------------------------------------------------------- bascule
RELANCE=0
revenir() {
    info "retour au code de départ ($ANCIEN_NOM)…"
    "${G[@]}" checkout -q "$ANCIEN"
    rendre_fichiers
    pipi || info "⚠ dépendances de départ non réinstallées : relancer pip à la main"
    if [ "$RELANCE" = 1 ]; then
        if [ -n "$LATEST_AVANT" ]; then
            sed -i "s/^LATEST_VERSION=.*/LATEST_VERSION=$LATEST_AVANT/" "$ENV_FILE"
        fi
        systemctl restart "$SERVICE"
    fi
    info "code de départ remis ; service $([ "$RELANCE" = 1 ] && echo relancé || echo 'jamais arrêté')"
}

if [ "$CLE_A_POSER" = 1 ]; then
    etape "Clé secrète"
    NOUVELLE="$("$DIR/venv/bin/python" -c 'import secrets;print(secrets.token_urlsafe(50))')"
    if grep -q '^SECRET_KEY=' "$ENV_FILE"; then
        sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$NOUVELLE|" "$ENV_FILE"
    else
        echo "SECRET_KEY=$NOUVELLE" >> "$ENV_FILE"
    fi
    info "SECRET_KEY tirée au sort"
fi

etape "Code $CIBLE et dépendances"
"${G[@]}" checkout -q "refs/tags/$CIBLE"
rendre_fichiers
if ! pipi; then revenir; echec "installation des dépendances de $CIBLE impossible"; fi
if ! gere check 2>&1 | sed 's/^/   /'; then revenir; echec "$CIBLE ne démarre pas avec ce .env (message ci-dessus)"; fi

etape "Migrations"
gere migrate --plan 2>&1 | sed 's/^/   /'
if ! gere migrate --noinput 2>&1 | sed 's/^/   /'; then
    APRES="$(infos_base 2>/dev/null | sed -n 's/^MIGRATIONS=//p')"
    if [ "${APRES:-x}" = "$(lire MIGRATIONS)" ]; then
        revenir
        echec "migration refusée, aucune appliquée : base et code inchangés"
    fi
    echec "migration interrompue après $((APRES - $(lire MIGRATIONS))) migration(s) appliquée(s). Service non relancé (ancien code en mémoire). Corriger la cause et relancer ce script ; sauvegarde : $SAUV"
fi
APRES="$(infos_base 2>/dev/null | sed -n 's/^MIGRATIONS=//p')"
MIGREES=$(( ${APRES:-0} - $(lire MIGRATIONS) ))
gere collectstatic --noinput -v 0

etape "Annonce et redémarrage"
ANNONCE=0
if [ "$PUBLIEE" = "$VERSION" ] || [ "$PUBLIEE" = inconnue ]; then
    if grep -q '^LATEST_VERSION=' "$ENV_FILE"; then
        sed -i "s/^LATEST_VERSION=.*/LATEST_VERSION=$VERSION/" "$ENV_FILE"
    else
        echo "LATEST_VERSION=$VERSION" >> "$ENV_FILE"
    fi
    ANNONCE=1
fi
RELANCE=1
systemctl restart "$SERVICE"
CODE_HTTP=000
for _ in $(seq 30); do
    systemctl is-active -q "$SERVICE" && sonder && break
    sleep 1
done
if ! systemctl is-active -q "$SERVICE" || ! sonder; then
    journalctl -u "$SERVICE" -n 30 --no-pager 2>/dev/null || true
    if [ "$MIGREES" = 0 ]; then
        revenir
        echec "le service ne répond pas en $CIBLE (HTTP $CODE_HTTP) : version de départ remise"
    fi
    echec "le service ne répond pas en $CIBLE (HTTP $CODE_HTTP), après $MIGREES migration(s) : voir le journal ci-dessus ; sauvegarde : $SAUV"
fi

echo
echo "Mise à jour terminée : $ANCIEN_NOM → $CIBLE"
info "sauvegarde   : $SAUV ($OBJETS objets)"
info "migrations   : $MIGREES appliquée(s)"
info "service      : actif, répond (HTTP $CODE_HTTP)"
if [ "$ANNONCE" = 1 ]; then
    info "annoncée     : LATEST_VERSION=$VERSION"
else
    info "NON annoncée : LATEST_VERSION=${LATEST_AVANT:-vide} (dépôt APT : ${PUBLIEE:-rien})"
    echo "Publier cicada $VERSION avec publish.sh, puis relancer : bash $0 $CIBLE" >&2
    exit 3
fi
