# Packaging CICADA

Ce répertoire contient tous les fichiers nécessaires pour créer le package Debian (.deb) de CICADA.

> **Voir aussi** : [Guide d'installation](../docs/INSTALLATION_GUIDE.md) (installation et mise à jour en production) | [Guide de test packaging](TESTING.md) (tests détaillés)

## Structure

```
packaging/
├── debian/              # Structure du package Debian
│   ├── DEBIAN/          # Métadonnées et scripts du package
│   ├── etc/             # Fichiers de configuration système
│   ├── usr/             # Binaires et fichiers partagés
│   └── var/             # Données persistantes
├── installer/            # Interface d'installation web (Flask)
│   ├── app.py           # Application Flask principale
│   ├── install_service.py  # Service d'installation
│   ├── templates/       # Templates HTML
│   └── static/          # CSS et JavaScript
└── build-deb.sh         # Script de construction du package
```

## Construction du package

### Prérequis

- `dpkg-deb` installé
- Accès root ou sudo

### Étapes

1. **Définir l'URL de l'API de suivi** (optionnel, valeur par défaut utilisée sinon) :

```bash
export TRACKING_API_URL="https://tracking.cicada.reserves-naturelles.org/api"
```

2. **Construire le package** (la version doit correspondre au tag des images sur ghcr.io) :

```bash
cd packaging
./build-deb.sh
# Ou pour une autre version (ex. release) :
VERSION=0.1.12 ./build-deb.sh
```

Le package sera créé dans `packaging/build/cicada_0.1.12_amd64.deb` (ou la version passée via `VERSION=...`)

### Installation du package

```bash
sudo dpkg -i packaging/build/cicada_*.deb
```

## Comment tester

Voir **[TESTING.md](TESTING.md)** pour le guide complet des tests.

En résumé, il existe 6 scripts de test :

| Script | Durée | Ce qu’il teste |
|--------|-------|----------------|
| `test-install-quick.sh` | ~30s | Fichiers installés (pas de Docker) |
| `test-install.sh` | ~5 min | Fichiers + services systemd + heartbeat |
| `test-install-full.sh` | ~10 min | Installation + systemd + interface web |
| `test-install-web.sh` | ~5 min | Interface web Flask (http://localhost:4567) |
| `test-install-web-full.sh` | ~10 min | Interface web + Docker (pull images GHCR) |
| **`test-upgrade-vm.sh`** | **10-20 min** | **Test d’upgrade v1→v2 en VM Multipass** |

```bash
# Tests rapides (conteneurs Docker)
./build-deb.sh
./test-install-quick.sh

# Test d’upgrade complet (VM Multipass, avant release)
./test-upgrade-vm.sh --from 0.1.12 --to 0.1.13
```

## Fichiers importants

- `debian/DEBIAN/control` : Métadonnées du package
- `debian/DEBIAN/postinst` : Script exécuté après l'installation
- `debian/etc/cicada/cicada.conf` : Configuration système
- `debian/usr/share/cicada/install/` : Interface d'installation web

## Notes

- **Images pré-buildées** : l'installation utilise les images Docker publiées sur GitHub Container Registry (`ghcr.io/rnf-si/cicada-backend`, `ghcr.io/rnf-si/cicada-frontend`). Aucune construction locale ; l'installateur ne fait que télécharger les images et configurer les paramètres (`.env`, ports, base de données, etc.).
- Le package ne contient pas le code backend/frontend, uniquement le `docker-compose.yml` (images uniquement), le dossier `docker/` (scripts d'init PostGIS) et l'interface d'installation.
- L'URL de l'API de suivi est fixée lors de la construction du package.
- Le token d'instance est généré automatiquement lors de l'installation.
- Les services systemd sont activés automatiquement.
