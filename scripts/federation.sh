#!/usr/bin/env bash
#
# Banc d'essai de l'exploration fédérée (#636).
#
# Pilote les trois briques — deux instances CICADA et le hub — depuis une seule
# commande. Chaque sous-commande encode une des chausse-trappes rencontrées au
# montage, qui coûtent toutes cher à rediagnostiquer :
#
#   - le hub DOIT être lancé avec son nom de projet, sinon son service `db`
#     détruit et recrée le conteneur de la base de l'instance principale ;
#   - l'instance CEN a besoin de trois arguments (-p, --env-file, deux -f) que
#     personne ne retape juste ;
#   - une base ayant vu l'ancienne branche a `0004_federation_instance_id` en
#     base et bloque au démarrage sur « column instance_id already exists » ;
#   - changer l'identité d'une instance périme tout son index, et la
#     publication échoue alors — franchement, mais après coup.
#
# Usage : scripts/federation.sh <commande> [cible]
# Cibles : rnf | cen | all   (défaut : all)
#
# Voir docs/MULTI_INSTANCE_LOCAL.md pour le détail de la topologie.

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

# --------------------------------------------------------------------------- #
# Les trois stacks
# --------------------------------------------------------------------------- #
RNF=(docker compose)
CEN=(docker compose -p cicada_cen --env-file .env.cen
     -f docker-compose.yml -f docker-compose.instance.yml)
HUB=(docker compose -f docker-compose.hub.yml --env-file .env.hub)

RNF_WEB=cicada_web
CEN_WEB=cicada_cen_web
HUB_API=cicada_hub_api

URL_RNF_UI=http://localhost
URL_RNF_API=http://localhost:8000
URL_CEN_UI=http://localhost:8081
URL_CEN_API=http://localhost:8001
URL_HUB=http://localhost:8002

# --------------------------------------------------------------------------- #
# Affichage
# --------------------------------------------------------------------------- #
if [ -t 1 ]; then
  GRAS='\033[1m'; VERT='\033[32m'; ROUGE='\033[31m'; JAUNE='\033[33m'; RAZ='\033[0m'
else
  GRAS=''; VERT=''; ROUGE=''; JAUNE=''; RAZ=''
fi

titre()   { printf "\n${GRAS}%s${RAZ}\n" "$*"; }
info()    { printf "  %s\n" "$*"; }
ok()      { printf "  ${VERT}✓${RAZ} %s\n" "$*"; }
alerte()  { printf "  ${JAUNE}!${RAZ} %s\n" "$*"; }
erreur()  { printf "  ${ROUGE}✗${RAZ} %s\n" "$*" >&2; }

# --------------------------------------------------------------------------- #
# Préalables
# --------------------------------------------------------------------------- #
verifier_env() {
  if [ ! -f .env.hub ]; then
    alerte ".env.hub absent — copié depuis .env.hub.example"
    cp .env.hub.example .env.hub
  fi
  if [ ! -f .env.cen ]; then
    erreur ".env.cen absent. Voir docs/MULTI_INSTANCE_LOCAL.md pour son contenu."
    exit 1
  fi
}

attendre() {
  local url="$1" nom="$2" limite="${3:-300}" debut
  debut=$(date +%s)
  until curl -sf -o /dev/null "$url"; do
    if [ $(( $(date +%s) - debut )) -gt "$limite" ]; then
      erreur "$nom ne répond toujours pas après ${limite}s ($url)"
      return 1
    fi
    sleep 3
  done
  ok "$nom"
}

# Une base ayant vu la branche avant la renumérotation porte
# `0004_federation_instance_id`. Django tente alors de rejouer le `0005` et
# échoue sur « column instance_id already exists ». Le correctif est un
# renommage d'enregistrement : la colonne, elle, est déjà là.
reparer_migration() {
  local conteneur_db="$1" nom="$2"
  local sql="UPDATE utilisateurs.django_migrations
             SET name='0005_federation_instance_id'
             WHERE app='search' AND name='0004_federation_instance_id';"
  if ! docker ps --format '{{.Names}}' | grep -qx "$conteneur_db"; then
    return 0
  fi
  local resultat
  resultat=$(docker exec "$conteneur_db" psql -U cicada_user -d cicada -tAc "$sql" 2>/dev/null || true)
  if [ "$resultat" = "UPDATE 1" ]; then
    alerte "$nom : historique de migration réaligné (0004 → 0005)"
  fi
}

# --------------------------------------------------------------------------- #
# Commandes
# --------------------------------------------------------------------------- #
# Ouvre les trois briques en onglets d'une SEULE fenêtre.
#
# Le hub n'a pas d'interface : son onglet pointe sur la sonde de disponibilité,
# la seule route qu'un navigateur puisse atteindre — les autres exigent l'en-tête
# `X-Hub-Token`, qu'une barre d'adresse ne sait pas poser. Cet onglet sert à
# répondre d'un coup d'œil à « le hub est-il debout ? », qui est la première
# question quand l'exploration du CEN renvoie une erreur.
#
# Les sessions des deux instances ne se marchent pas dessus, même dans une seule
# fenêtre : ports différents = origines différentes, donc `localStorage`
# séparés. On peut être connecté aux deux à la fois, sous des comptes différents.
cmd_open() {
  local navigateur=''
  for candidat in google-chrome google-chrome-stable chromium chromium-browser xdg-open; do
    if command -v "$candidat" >/dev/null 2>&1; then navigateur="$candidat"; break; fi
  done

  # Une brique qui ne répond pas est signalée et non ouverte : un onglet en
  # erreur se prend facilement pour un bug applicatif.
  local urls=() etiquettes=()
  for couple in "RNF $URL_RNF_UI/exploration" \
                "CEN $URL_CEN_UI/exploration" \
                "HUB $URL_HUB/api/health/"; do
    local nom="${couple% *}" url="${couple##* }"
    if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$url" || echo 000)" = 200 ]; then
      urls+=("$url"); etiquettes+=("$nom $url")
    else
      alerte "$nom ne répond pas — onglet non ouvert ($url)"
    fi
  done

  if [ ${#urls[@]} -eq 0 ]; then
    erreur "Rien à ouvrir. Lancer « federation.sh up » d'abord."
    return 1
  fi

  if [ -z "$navigateur" ]; then
    erreur "Aucun navigateur trouvé. Ouvrir à la main :"
    for etiquette in "${etiquettes[@]}"; do info "$etiquette"; done
    return 1
  fi

  titre "Ouverture — une fenêtre, ${#urls[@]} onglets ($navigateur)"
  if [ "$navigateur" = xdg-open ]; then
    # xdg-open ne prend qu'une URL : le navigateur par défaut les groupera
    # généralement en onglets de la fenêtre existante.
    for url in "${urls[@]}"; do "$navigateur" "$url" >/dev/null 2>&1 & sleep 1; done
  else
    # Une seule invocation avec toutes les URL : Chrome ouvre une fenêtre et y
    # met un onglet par URL. Les lancer une par une donnerait N fenêtres.
    "$navigateur" --new-window "${urls[@]}" >/dev/null 2>&1 &
  fi

  for etiquette in "${etiquettes[@]}"; do ok "$etiquette"; done
  info ""
  info "Connexion sur les deux instances : admin@test.fr / Test123!"
  info "L'onglet HUB est sa sonde de disponibilité — le hub n'a pas d'interface."
}

cmd_up() {
  local cible=all ouvrir=0
  for argument in "$@"; do
    case "$argument" in
      --open|-o) ouvrir=1 ;;
      all|hub|rnf|cen) cible="$argument" ;;
      *) erreur "Argument inconnu : $argument"; exit 1 ;;
    esac
  done
  verifier_env

  if [ "$cible" = all ] || [ "$cible" = hub ]; then
    titre "Hub d'exploration"
    "${HUB[@]}" up -d
    attendre "$URL_HUB/api/health/" "hub  $URL_HUB"
  fi

  if [ "$cible" = all ] || [ "$cible" = rnf ]; then
    titre "Instance RNF"
    "${RNF[@]}" up -d db redis
    reparer_migration cicada_db RNF
    "${RNF[@]}" up -d
    attendre "$URL_RNF_API/api/auth/health/" "API  $URL_RNF_API" 600
    attendre "$URL_RNF_UI/" "UI   $URL_RNF_UI" 900
  fi

  if [ "$cible" = all ] || [ "$cible" = cen ]; then
    titre "Instance CEN"
    "${CEN[@]}" up -d db redis
    reparer_migration cicada_cen_db CEN
    "${CEN[@]}" up -d
    attendre "$URL_CEN_API/api/auth/health/" "API  $URL_CEN_API" 600
    attendre "$URL_CEN_UI/" "UI   $URL_CEN_UI" 900
  fi

  cmd_status
  [ "$ouvrir" = 1 ] && cmd_open
  return 0
}

cmd_down() {
  local cible="${1:-all}"
  if [ "$cible" = all ] || [ "$cible" = cen ]; then
    titre "Arrêt du CEN";  "${CEN[@]}" down
  fi
  if [ "$cible" = all ] || [ "$cible" = hub ]; then
    titre "Arrêt du hub";  "${HUB[@]}" down
  fi
  if [ "$cible" = rnf ]; then
    titre "Arrêt de RNF";  "${RNF[@]}" down
  elif [ "$cible" = all ]; then
    # L'instance principale est le stack de travail : on ne la coupe pas sans
    # qu'on l'ait explicitement demandé.
    alerte "RNF laissé tourner — « down rnf » pour l'arrêter aussi"
  fi
}

_mode_de() {
  docker exec "$1" python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.development')
django.setup()
from django.conf import settings
print(f'{settings.CICADA_INSTANCE_ID}|{settings.CICADA_EXPLORATION_SOURCE}')
" 2>/dev/null | tail -1
}

cmd_status() {
  titre "Services"
  for couple in "hub $URL_HUB/api/health/" \
                "RNF API $URL_RNF_API/api/auth/health/" \
                "RNF UI  $URL_RNF_UI/" \
                "CEN API $URL_CEN_API/api/auth/health/" \
                "CEN UI  $URL_CEN_UI/"; do
    local nom="${couple% *}" url="${couple##* }"
    local code
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$url" || echo 000)
    if [ "$code" = 200 ]; then ok "$(printf '%-8s %s' "$nom" "$url")"
    else erreur "$(printf '%-8s %s  (HTTP %s)' "$nom" "$url" "$code")"; fi
  done

  titre "Exploration de chaque instance"
  for couple in "RNF $RNF_WEB" "CEN $CEN_WEB"; do
    local nom="${couple% *}" conteneur="${couple##* }"
    if docker ps --format '{{.Names}}' | grep -qx "$conteneur"; then
      local etat; etat=$(_mode_de "$conteneur")
      local source="${etat##*|}"
      if [ "$source" = hub ]; then
        info "$(printf '%-4s identité « %s » → relayée vers le hub' "$nom" "${etat%%|*}")"
      else
        info "$(printf '%-4s identité « %s » → index local' "$nom" "${etat%%|*}")"
      fi
    else
      alerte "$nom arrêté"
    fi
  done

  titre "Index agrégé du hub"
  if docker ps --format '{{.Names}}' | grep -qx "$HUB_API"; then
    "${HUB[@]}" exec -T db psql -U cicada_user -d cicada_hub -tAF' ' -c "
      SELECT p.instance_id, count(DISTINCT p.id), count(c.id)
      FROM ccd_search.t_plan_indexe p
      LEFT JOIN ccd_search.t_recherche_contenu c ON c.id_plan_indexe = p.id
      GROUP BY 1 ORDER BY 1;" 2>/dev/null \
      | while read -r instance plans documents; do
          [ -n "$instance" ] && info "$(printf '%-6s %3s plans, %4s documents' "$instance" "$plans" "$documents")"
        done
    local total
    total=$("${HUB[@]}" exec -T db psql -U cicada_user -d cicada_hub -tAc \
      "SELECT count(*) FROM ccd_search.t_plan_indexe;" 2>/dev/null | tr -d '[:space:]')
    [ "${total:-0}" = 0 ] && alerte "hub vide — lancer « federation.sh push »"
  else
    alerte "hub arrêté"
  fi
  echo
}

_conteneur_de() {
  case "$1" in
    rnf) echo "$RNF_WEB" ;;
    cen) echo "$CEN_WEB" ;;
    *)   erreur "Cible inconnue : $1 (attendu rnf ou cen)"; exit 1 ;;
  esac
}

cmd_reindex() {
  local cible="${1:-all}"
  for instance in $( [ "$cible" = all ] && echo "rnf cen" || echo "$cible" ); do
    titre "Réindexation — $instance"
    # --purge : les documents déjà indexés portent l'identité qu'ils avaient à
    # l'indexation. Sans purge, un changement d'identité laisse un index que
    # plus aucune publication ne retrouve.
    docker exec "$(_conteneur_de "$instance")" \
      python manage.py rebuild_search_index --purge 2>&1 | grep -vE 'psycopg|DEBUG' | tail -3
  done
}

cmd_push() {
  # « push --dry-run » sans cible : la première option ne doit pas être prise
  # pour un nom d'instance.
  local cible=all
  if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then
    cible="$1"; shift
  fi

  for instance in $( [ "$cible" = all ] && echo "rnf cen" || echo "$cible" ); do
    titre "Dépôt vers le hub — $instance"
    docker exec "$(_conteneur_de "$instance")" \
      python manage.py push_federation "$@" 2>&1 | grep -vE 'psycopg|DEBUG' | tail -12
  done
}

cmd_mode() {
  local source="${1:-}" cible="${2:-cen}"
  case "$source" in
    local|hub) ;;
    *) erreur "Usage : federation.sh mode <local|hub> [rnf|cen]"; exit 1 ;;
  esac

  local fichier
  case "$cible" in
    rnf) fichier=.env ;;
    cen) fichier=.env.cen ;;
    *)   erreur "Cible inconnue : $cible"; exit 1 ;;
  esac

  if grep -q '^CICADA_EXPLORATION_SOURCE=' "$fichier"; then
    sed -i "s#^CICADA_EXPLORATION_SOURCE=.*#CICADA_EXPLORATION_SOURCE=$source#" "$fichier"
  else
    printf '\n# Source de l'"'"'exploration (#636)\nCICADA_EXPLORATION_SOURCE=%s\n' "$source" >> "$fichier"
  fi
  ok "$fichier : exploration → $source"

  titre "Redémarrage du backend $cible"
  if [ "$cible" = rnf ]; then "${RNF[@]}" up -d web; else "${CEN[@]}" up -d web; fi
  attendre "$( [ "$cible" = rnf ] && echo "$URL_RNF_API" || echo "$URL_CEN_API" )/api/auth/health/" \
           "API $cible" 300
}

cmd_check() {
  titre "Scénario de bout en bout"
  local jeton
  jeton=$(grep '^HUB_READ_TOKEN=' .env.hub | cut -d= -f2-)
  if [ -z "$jeton" ]; then erreur "HUB_READ_TOKEN absent de .env.hub"; exit 1; fi

  local corps
  corps=$(curl -s -H "X-Hub-Token: $jeton" "$URL_HUB/api/exploration/contenus/") || {
    erreur "hub injoignable"; exit 1; }

  python3 - "$corps" <<'PY'
import json, sys
d = json.loads(sys.argv[1])
total = d['compteurs']['tout']
instances = sorted({r['instance_id'] for r in d['results']})
print(f"  {total} documents explorables")
print(f"  instances représentées sur la première page : {instances or '—'}")
if total == 0:
    print("  ! index vide — lancer « federation.sh push »")
elif len(instances) < 2:
    print("  ! une seule instance visible — les deux ont-elles publié ?")
else:
    print("  ✓ recherche transverse opérationnelle")
PY
  echo
}

cmd_reset_hub() {
  titre "Remise à zéro du hub"
  alerte "La base du hub va être supprimée. Les instances ne sont pas touchées."
  read -r -p "  Confirmer ? [o/N] " reponse
  case "$reponse" in
    o|O|oui|OUI) ;;
    *) info "Annulé."; return 0 ;;
  esac
  "${HUB[@]}" down -v
  "${HUB[@]}" up -d
  attendre "$URL_HUB/api/health/" "hub  $URL_HUB" 600
  info "Relancer « federation.sh push » pour repeupler l'index."
}

cmd_logs() {
  local cible="${1:-hub}"
  case "$cible" in
    hub) "${HUB[@]}" logs -f hub ;;
    rnf) "${RNF[@]}" logs -f web ;;
    cen) "${CEN[@]}" logs -f web ;;
    *)   erreur "Cible inconnue : $cible (hub, rnf ou cen)"; exit 1 ;;
  esac
}

cmd_test() {
  titre "Suite du hub"
  "${HUB[@]}" exec -T hub pytest -q 2>&1 | tail -5
  titre "Suite fédération de CICADA"
  docker exec "$RNF_WEB" pytest tests/apps/search/ -q -p no:logging 2>&1 | tail -4
}

aide() {
  cat <<'TXT'
Banc d'essai de l'exploration fédérée (#636)

  scripts/federation.sh <commande> [cible]

Commandes
  up [all|hub|rnf|cen] [--open]  démarre les stacks, attend qu'ils répondent,
                                 et ouvre les onglets avec --open
  open                      une fenêtre, 3 onglets (RNF, CEN, sonde du hub)
  down [all|hub|rnf|cen]    arrête (« all » épargne RNF, stack de travail)
  status                    services, mode d'exploration, contenu du hub
  check                     vérifie que la recherche est bien transverse

  reindex [all|rnf|cen]     reconstruit l'index local (--purge)
  push [all|rnf|cen] [...]  dépose l'index sur le hub
                            arguments supplémentaires passés à la commande
                            (--dry-run, --sans-fiche, --page-size N)

  mode <local|hub> [rnf|cen]   bascule la source de l'exploration et redémarre
  logs [hub|rnf|cen]           suit les journaux
  test                         lance les deux suites de tests
  reset-hub                    vide la base du hub et le relance

Adresses
  RNF  http://localhost        API :8000     Mailpit :8025
  CEN  http://localhost:8081   API :8001     Mailpit :8026
  Hub  (pas d'interface)       API :8002

Connexion sur les deux instances : admin@test.fr / Test123!

Détail de la topologie : docs/MULTI_INSTANCE_LOCAL.md
TXT
}

# --------------------------------------------------------------------------- #

case "${1:-aide}" in
  up)        shift; cmd_up "$@" ;;
  open)      cmd_open ;;
  down)      cmd_down "${2:-all}" ;;
  status)    cmd_status ;;
  check)     cmd_check ;;
  reindex)   cmd_reindex "${2:-all}" ;;
  push)      shift; cmd_push "$@" ;;
  mode)      cmd_mode "${2:-}" "${3:-cen}" ;;
  logs)      cmd_logs "${2:-hub}" ;;
  test)      cmd_test ;;
  reset-hub) cmd_reset_hub ;;
  aide|-h|--help|help) aide ;;
  *)         erreur "Commande inconnue : $1"; echo; aide; exit 1 ;;
esac
