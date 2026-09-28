#!/usr/bin/env bash
#
# Genere les SBOM CycloneDX du depot et, optionnellement, les envoie a
# Dependency-Track.
#
#   ./scripts/generate-sbom.sh                # genere sbom/*.cdx.json
#   ./scripts/generate-sbom.sh --avec-dev     # inclut les dependances npm de dev
#   ./scripts/generate-sbom.sh --envoi        # genere puis envoie
#
# Variables d'environnement :
#   DT_URL       API server Dependency-Track. A defaut, ~/.config/dependency-track/url
#                puis le serveur RNF.
#   DT_API_KEY   cle d'API. A defaut, ~/.config/dependency-track/api.key
#   DT_PROJET    prefixe des projets Dependency-Track (defaut : cicada)
#   DT_VERSION   version des projets Dependency-Track (defaut : prod)
#   APP_VERSION  version applicative inscrite dans les SBOM
#
set -euo pipefail
shopt -s nullglob

RACINE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SORTIE="$RACINE/sbom"
OUTILS="$RACINE/.sbom-tools"
CYCLONEDX_NPM_VERSION="6.0.1"

# Fixe plutot que deduit du repertoire : le clone s appelle « Cicada » et les
# projets Dependency-Track sont en minuscules.
PROJET="${DT_PROJET:-cicada}"
VERSION="${DT_VERSION:-prod}"
# Version applicative inscrite dans les SBOM. En CI on y passe le tag de la
# release ; en local, le dernier tag du depot est la valeur la plus proche.
VERSION_APP="${APP_VERSION:-$(git describe --tags --abbrev=0 2>/dev/null || echo 0.0.0)}"

AVEC_DEV=0
ENVOI=0
for arg in "$@"; do
  case "$arg" in
    --avec-dev) AVEC_DEV=1 ;;
    --envoi)    ENVOI=1 ;;
    -h|--help)  sed -n '2,17p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "Option inconnue : $arg" >&2; exit 1 ;;
  esac
done

mkdir -p "$SORTIE"

# Nom du projet Dependency-Track pour un repertoire donne : le prefixe seul a la
# racine, sinon prefixe-repertoire (backend/ -> ancrage-backend).
nom_projet() {
  local dossier="$1"
  if [ "$dossier" = "$RACINE" ]; then
    echo "$PROJET"
  else
    echo "$PROJET-$(basename "$dossier")"
  fi
}

installer_cyclonedx_py() {
  if [ ! -x "$OUTILS/bin/cyclonedx-py" ]; then
    echo "  installation de cyclonedx-bom dans $OUTILS"
    python3 -m venv "$OUTILS"
    "$OUTILS/bin/pip" install --quiet --upgrade pip cyclonedx-bom
  fi
}

# `cyclonedx-py requirements` ne deduit aucun composant racine : sans lui le
# graphe de dependances arrive incomplet dans Dependency-Track.
injecter_racine() {
  "$OUTILS/bin/python" - "$1" "$VERSION_APP" "$2" <<'PY'
import json, sys

chemin, version, nom = sys.argv[1], sys.argv[2], sys.argv[3]
with open(chemin) as f:
    bom = json.load(f)

if not bom.get("metadata", {}).get("component"):
    racine = {
        "type": "application",
        "bom-ref": f"{nom}@{version}",
        "name": nom,
        "version": version,
    }
    bom.setdefault("metadata", {})["component"] = racine
    bom.setdefault("dependencies", []).insert(0, {
        "ref": racine["bom-ref"],
        "dependsOn": sorted(c["bom-ref"] for c in bom.get("components", [])),
    })
    with open(chemin, "w") as f:
        json.dump(bom, f, indent=2, sort_keys=True)
PY
}

TROUVE=0

# --- Python : requirements.txt -----------------------------------------------
for manifeste in "$RACINE"/requirements.txt "$RACINE"/*/requirements.txt; do
  if [ ! -f "$manifeste" ]; then continue; fi
  dossier="$(dirname "$manifeste")"
  nom="$(nom_projet "$dossier")"
  echo "» $nom (python, requirements.txt)"
  installer_cyclonedx_py
  "$OUTILS/bin/cyclonedx-py" requirements --sv 1.6 --of JSON \
    --mc-type application -o "$SORTIE/$nom.cdx.json" "$manifeste"
  injecter_racine "$SORTIE/$nom.cdx.json" "$nom"
  TROUVE=1
done

# --- Python : poetry ---------------------------------------------------------
for manifeste in "$RACINE"/poetry.lock "$RACINE"/*/poetry.lock; do
  if [ ! -f "$manifeste" ]; then continue; fi
  dossier="$(dirname "$manifeste")"
  nom="$(nom_projet "$dossier")"
  echo "» $nom (python, poetry)"
  installer_cyclonedx_py
  "$OUTILS/bin/cyclonedx-py" poetry --sv 1.6 --of JSON \
    -o "$SORTIE/$nom.cdx.json" "$dossier"
  TROUVE=1
done

# --- npm ---------------------------------------------------------------------
for manifeste in "$RACINE"/package-lock.json "$RACINE"/*/package-lock.json; do
  if [ ! -f "$manifeste" ]; then continue; fi
  dossier="$(dirname "$manifeste")"
  nom="$(nom_projet "$dossier")"
  echo "» $nom (npm)"

  # cyclonedx-npm s'appuie sur `npm ls` : l'arbre doit etre reellement installe.
  if [ ! -d "$dossier/node_modules" ]; then
    echo "  node_modules absent, npm ci en cours"
    (cd "$dossier" && npm ci --silent)
  fi

  options=(--spec-version 1.6 --output-format JSON)
  if [ "$AVEC_DEV" -eq 0 ]; then
    options+=(--omit dev)
  fi
  (cd "$dossier" && npx --yes "@cyclonedx/cyclonedx-npm@$CYCLONEDX_NPM_VERSION" \
    "${options[@]}" --output-file "$SORTIE/$nom.cdx.json")

  # Un manifeste qui ne porte que de l'outillage de dev (commitlint a la racine)
  # donne un SBOM vide : l'envoyer creerait un projet fantome dans Dependency-Track.
  if [ "$(python3 -c "import json;print(len(json.load(open('$SORTIE/$nom.cdx.json')).get('components', [])))")" -eq 0 ]; then
    echo "  aucune dependance de production, SBOM ignore"
    rm -f "$SORTIE/$nom.cdx.json"
    continue
  fi
  TROUVE=1
done

if [ "$TROUVE" -eq 0 ]; then
  echo "Aucune chaine de dependances detectee sous $RACINE" >&2
  echo "Ajouter l'ecosysteme manquant dans ce script." >&2
  exit 1
fi

echo
for f in "$SORTIE"/*.cdx.json; do
  echo "  $f — $(python3 -c "import json;print(len(json.load(open('$f'))['components']))") composants"
done

# --- Envoi vers Dependency-Track ---------------------------------------------
if [ "$ENVOI" -eq 0 ]; then
  exit 0
fi

# Identifiants Dependency-Track, partages par tous les depots :
#   $CONFIG/url      URL de l'API server (facultatif)
#   $CONFIG/api.key  cle d'API (mode 600)
# Les variables d'environnement restent prioritaires : c'est par elles que la CI
# fournit ses secrets, sans jamais toucher au disque.
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/dependency-track"
DT_URL_DEFAUT="https://dependencytrack.reserves-naturelles.org"

if [ -z "${DT_URL:-}" ] && [ -r "$CONFIG/url" ]; then
  DT_URL="$(tr -d '[:space:]' < "$CONFIG/url")"
fi
if [ -z "${DT_URL:-}" ]; then
  DT_URL="$DT_URL_DEFAUT"
fi

if [ -z "${DT_API_KEY:-}" ] && [ -r "$CONFIG/api.key" ]; then
  DT_API_KEY="$(tr -d '[:space:]' < "$CONFIG/api.key")"
fi
if [ -z "${DT_API_KEY:-}" ]; then
  echo "Aucune clé d'API : définir DT_API_KEY ou renseigner $CONFIG/api.key" >&2
  exit 1
fi

# DT_URL doit viser l'API server et non l'interface web, qui repond 405 a tout
# POST. Le frontend sert index.html en repli sur /api/version et ce HTML contient
# le nom du produit : on teste donc le champ JSON exact.
if ! curl -sS -f -m 10 "$DT_URL/api/version" | grep -q '"application":"Dependency-Track"'; then
  echo "DT_URL ne pointe pas vers l'API server de Dependency-Track : $DT_URL" >&2
  exit 1
fi

for f in "$SORTIE"/*.cdx.json; do
  nom="$(basename "$f" .cdx.json)"
  echo "» Envoi de $nom"
  curl -sS -f \
    -X POST "$DT_URL/api/v1/bom" \
    -H "X-Api-Key: $DT_API_KEY" \
    -F "projectName=$nom" \
    -F "projectVersion=$VERSION" \
    -F "autoCreate=true" \
    -F "bom=@$f"
  echo
done

echo "Terminé — voir $DT_URL"
