# Packaging CICADA

Ce répertoire contient tous les fichiers nécessaires pour créer le package Debian (.deb) de CICADA.

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
export TRACKING_API_URL="https://tracking.cicada.rnf.fr/api"
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

Après avoir construit le package (`./build-deb.sh`), tu peux tester à trois niveaux.

### 1. Test rapide (sans réseau, ~30 s)

Vérifie que le .deb installe bien tous les fichiers (compose, installer, `docker/postgres/init.sql`, config, services). **Docker n’est pas installé** dans le conteneur, donc les dépendances sont forcées.

```bash
cd packaging
./build-deb.sh
./test-install-quick.sh
```

À la fin : vérification des fichiers, affichage de `cicada.conf` et du token. Nettoyage : `docker rm -f cicada-test-quick`.

### 2. Test avec Docker dans le conteneur (~5–10 min)

Installe le package dans un conteneur Debian avec **Docker + Docker Compose** installés (sans lancer l’installateur web). Utile pour valider postinst, structure des fichiers et scripts.

```bash
cd packaging
./build-deb.sh
./test-install.sh
```

À la fin : vérifications + test du script heartbeat. Nettoyage : `docker rm -f cicada-test-install`.

### 3. Test de l’interface web d’installation (pull des images)

Lance un conteneur avec le **socket Docker** monté, installe le package et démarre l’installateur Flask. Tu peux ouvrir l’interface dans le navigateur et lancer une installation réelle (pull des images GHCR + `docker compose up`).

**Prérequis :** accès réseau à **ghcr.io** (GitHub Container Registry) depuis la machine qui lance le conteneur (les commandes Docker s’exécutent côté hôte via le socket).

```bash
cd packaging
./build-deb.sh
./test-install-web.sh
```

Puis dans le navigateur : **http://localhost:4567**. Remplis le formulaire (admin, domaine, port frontend, mot de passe DB, etc.) et lance l’installation. L’installateur va :

1. Générer le `.env`
2. Faire `docker compose pull` (images `ghcr.io/rnf-si/cicada-*`)
3. Lancer `docker compose up -d` (avec ou sans `--profile with-db`)

Si les images ne sont pas encore publiées sur GHCR (ex. branche de dev), le **pull échouera** ; dans ce cas le test rapide et le test « avec Docker » restent valides pour la structure du package et l’installateur.

Nettoyage : `docker rm -f cicada-test-web`.

### Tester sur une vraie machine (recommandé avant release)

1. Sur une VM ou un serveur Debian/Ubuntu avec Docker installé :
2. Transférer le .deb puis : `sudo dpkg -i cicada_*.deb`
3. Aller sur `http://<machine>:4567` (ou le port configuré dans `cicada.conf`)
4. Compléter le formulaire et vérifier que les conteneurs démarrent et que l’app est accessible sur le port frontend choisi.

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
