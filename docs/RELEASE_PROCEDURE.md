# Procédure de mise en production CICADA

Cette note décrit les étapes pour publier une nouvelle version : images Docker, package .deb et dépôt APT.

## Vue d’ensemble

- Les **images Docker** (backend, frontend) sont construites et poussées sur GHCR lors d’un **push de tag** `v*` (ex. `v0.1.13`) — voir `.github/workflows/docker-publish.yml`. En pratique : merge des changements sur `main`, puis création et push du tag.
- Le **package .deb** est construit par la CI au **même moment** (workflow `.github/workflows/build-deb.yml`) : un seul tag déclenche images Docker + .deb avec la même version.
- La **publication sur le dépôt APT** (reprepro, signature GPG, mise en ligne) reste **manuelle** : télécharger l’artefact .deb depuis l’onglet Actions et l’ajouter au repo.

## 1. Préparer la version

- Décider du numéro de version (ex. `0.1.13`).
- Les fichiers `packaging/debian/DEBIAN/control` et `packaging/debian/etc/cicada/cicada.conf` contiennent une version par défaut ; le script `build-deb.sh` et la CI **écrasent** cette version au moment du build via la variable `VERSION`. Inutile de les modifier à la main pour une release.

## 2. Créer le tag et pousser (Docker + .deb en CI)

Une fois les changements mergés sur `main` :

```bash
git checkout main
git pull
git tag v0.1.13   # remplacer par la version choisie
git push origin v0.1.13
```

**Effets :**

- Le workflow **Docker Build & Push** s’exécute et publie les images `ghcr.io/rnf-si/cicada-backend:0.1.13`, `ghcr.io/rnf-si/cicada-frontend:0.1.13` (et `:latest`).
- Le workflow **Build Debian package** (voir ci‑dessous) s’exécute et produit un artefact `cicada_0.1.13_amd64.deb` (téléchargeable depuis l’onglet Actions ou la Release GitHub si vous en créez une).

La version du .deb est dérivée du tag (`v0.1.13` → `0.1.13`), donc elle reste alignée avec les images Docker.

## 3. Construire le .deb en local (alternative)

Si vous préférez ne pas utiliser la CI :

```bash
cd packaging
VERSION=0.1.13 TRACKING_API_URL="https://tracking.cicada.reserves-naturelles.org/api" ./build-deb.sh
```

Le fichier généré est `packaging/build/cicada_0.1.13_amd64.deb`.

## 4. Publier sur le dépôt APT

Sur la machine qui héberge le dépôt APT (ex. `apt.cicada.reserves-naturelles.org`) :

### 4.1 Récupérer le .deb

- Soit télécharger l’artefact depuis l’Action GitHub (workflow « Build Debian package »).
- Soit copier le fichier construit en local (voir §3).

### 4.2 Ajouter le paquet au dépôt (avec reprepro)

```bash
# Exemple : dépôt dans /var/www/repos/cicada (ou votre chemin)
cd /var/www/repos/cicada   # ou le répertoire de votre repo

# Ajouter le paquet à la distribution "stable"
reprepro includedeb stable /chemin/vers/cicada_0.1.13_amd64.deb

# Vérifier
reprepro list stable
```

Si vous utilisez **dpkg-scanpackages** (structure pool + dists) au lieu de reprepro, régénérer les index après avoir copié le .deb dans `pool/main/`, puis mettre à jour `dists/stable/...` comme d’habitude.

### 4.3 Signature GPG du dépôt

Si le dépôt est signé (recommandé) :

- Les commandes `reprepro` mettent à jour les fichiers `Release` et les signatures si la configuration GPG de reprepro est en place.
- Sinon, régénérer manuellement les signatures selon votre procédure (ex. `dpkg-scanpackages` + `apt-ftparchive release` + `gpg -u ... -abs -o Release.gpg Release`).

### 4.4 Vérification côté client

Sur une machine de test :

```bash
sudo apt update
apt-cache policy cicada
# Une nouvelle version 0.1.13 doit apparaître si le dépôt est à jour
sudo apt install cicada
```

## 5. Résumé du flux recommandé

| Étape | Action |
|-------|--------|
| 1 | Développement et merge sur `main` (éventuellement via PR). |
| 2 | Créer et pousser le tag `vX.Y.Z` → CI build les images Docker et le .deb. |
| 3 | Télécharger l’artefact .deb depuis GitHub Actions (ou le construire en local avec la même `VERSION`). |
| 4 | Sur le serveur du dépôt APT : `reprepro includedeb stable cicada_X.Y.Z_amd64.deb` (et signature si besoin). |
| 5 | Vérifier avec `apt update` et `apt install cicada` sur un client. |

## 6. Variables utiles pour le build du .deb

- **VERSION** : doit être identique au tag des images Docker (ex. `0.1.13` pour le tag `v0.1.13`).
- **TRACKING_API_URL** : URL de l’API de suivi (injectée dans `cicada.conf`). En CI, la valeur par défaut du script ou du workflow peut être adaptée (ex. `https://tracking.cicada.reserves-naturelles.org/api`).

## 7. En cas de release manuelle (sans tag)

Si vous publiez une version sans tag (ou sans CI) :

1. Construire les images Docker à la main, les tagger et les pousser vers GHCR avec la version choisie.
2. Construire le .deb avec `VERSION=X.Y.Z ./build-deb.sh`.
3. Suivre les étapes §4 pour la publication APT.
