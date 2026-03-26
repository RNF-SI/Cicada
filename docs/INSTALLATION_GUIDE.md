# Guide d'installation CICADA

## Installation via APT

### Prérequis

- Système d'exploitation : Debian 11+ ou Ubuntu 20.04+
- Docker et Docker Compose installés
- Accès root ou sudo
- **Si base de données externe** : PostgreSQL 17+ avec PostGIS 3.5+ installé sur le serveur

### Étapes d'installation

#### 1. Ajouter le repository APT

Si le repository APT est déjà configuré sur le serveur, passez directement à l'étape 2.

```bash
# Ajouter la clé GPG (remplacez l'URL par celle fournie par votre administrateur)
curl -fsSL https://apt.cicada.reserves-naturelles.org/cicada-repo-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cicada-archive-keyring.gpg

# Ajouter le repository
echo "deb [signed-by=/usr/share/keyrings/cicada-archive-keyring.gpg] https://apt.cicada.reserves-naturelles.org stable main" | sudo tee /etc/apt/sources.list.d/cicada.list

# Mettre à jour la liste des packages
sudo apt update
```

#### 2. Installer CICADA

```bash
sudo apt-get update
sudo apt-get install cicada
```

L'installation va :
- Installer les fichiers nécessaires (scripts, docker-compose, installeur web)
- Générer un token d'instance unique
- Démarrer le serveur d'installation web sur le port 4567

> **Note** : si le système vous demande de redémarrer des services (dbus, getty, systemd-logind), vous pouvez ignorer — ce sont des services système sans rapport avec CICADA.

#### 3. Préparer la base PostgreSQL (recommandé en production)

En production, il est **fortement recommandé** d’utiliser un PostgreSQL installé nativement sur le serveur plutôt que dans un conteneur Docker. Ainsi les données survivent à toute mise à jour, suppression ou recréation des conteneurs.

> **Alternative** : si vous préférez tout dans Docker (développement, test), vous pouvez passer cette étape et choisir "Nouvelle instance Docker" dans le formulaire (étape 5).

##### Prérequis

- PostgreSQL 17+ avec PostGIS 3.5+ installé sur le serveur
- `pg_hba.conf` autorisant les connexions depuis le réseau Docker (par défaut `172.17.0.0/16`)
- `listen_addresses = ‘*’` dans `postgresql.conf` (ou au minimum l’IP Docker `172.17.0.1`)

##### Vérifications

```bash
# Vérifier PostgreSQL et PostGIS
psql --version                              # PostgreSQL 17+
apt list --installed 2>/dev/null | grep postgis  # postgis-3 installé

# Vérifier que PostgreSQL écoute sur toutes les interfaces
sudo -u postgres psql -c "SHOW listen_addresses;"
# Doit retourner ‘*’ ou inclure l’IP Docker

# Trouver l’IP Docker (les conteneurs utiliseront cette IP pour se connecter)
ip addr show docker0 | grep ‘inet ‘
# Typiquement : 172.17.0.1
```

##### Créer la base et initialiser les schémas

Le script `cicada-prepare-db` (installé par le package) fait tout automatiquement : vérification des prérequis, création de l’utilisateur et de la base, exécution de `init.sql` (extensions, 12 schémas, permissions), et validation du résultat.

```bash
# Une seule commande — le script est interactif (demande le mot de passe)
sudo cicada-prepare-db
```

Options disponibles :

```bash
sudo cicada-prepare-db --help                         # Aide
sudo cicada-prepare-db --password SECRET              # Mode non-interactif
sudo cicada-prepare-db --db-name mabase --db-user monuser  # Noms personnalisés
```

Le script affichera à la fin les paramètres exacts à utiliser dans le formulaire d’installation web. **Notez bien le mot de passe**, il vous sera demandé à l’étape suivante.

#### 4. Accéder à l’interface d’installation

Ouvrez votre navigateur :

```
http://votre-serveur:4567
```

> **Si la page est inaccessible** : vérifiez que le service tourne avec `sudo systemctl status cicada-installer`. Si inactif, relancez-le : `sudo systemctl restart cicada-installer`.

#### 5. Remplir le formulaire d’installation

Le formulaire comporte 5 sections :

**Compte administrateur :**
- Email, mot de passe, nom, prénom du premier administrateur

**Configuration du site :**
- Nom de domaine (ex. `cicada.mon-organisme.org`)
- Présence d’Apache/Nginx (voir détails ci-dessous)
- Port du frontend si Apache/Nginx (ex. `8080`)

**Base de données PostgreSQL :**
- **Type** : "Instance existante" (si étape 3 faite) ou "Docker" (sinon)
- **Hôte** : l’IP Docker affichée par `cicada-prepare-db` (typiquement `172.17.0.1`). **Ne pas mettre `localhost`** — les conteneurs Docker ne peuvent pas accéder au `localhost` du serveur hôte.
- **Port** : `5432`
- **Nom, utilisateur, mot de passe** : ceux définis à l’étape 3

**Redis :** laisser les valeurs par défaut (Redis est géré dans Docker)

**Email (SMTP) :** si vous souhaitez que CICADA envoie des emails (notifications, inscriptions) :
- Serveur SMTP, port, TLS, authentification, adresse d’expéditeur
- Si non configuré, les emails seront affichés dans les logs (pas d’envoi réel)

**RGPD (optionnel) :** consentement pour partager les infos de l’instance avec les mainteneurs

**Question « Un serveur Apache ou Nginx est-il déjà présent sur ce serveur ? »**
- **Si vous ne cochez pas** : Traefik est utilisé sur les ports 80 et 443 (HTTPS avec Let’s Encrypt). Aucune configuration Apache/Nginx à prévoir.
- **Si vous cochez** : pas de Traefik. Le frontend est exposé sur un port que vous choisissez (ex. 8080). Vous devrez configurer un virtual host dédié sur votre Apache ou Nginx pour proxyfier le trafic vers ce port.

#### 6. Lancer l’installation

Cliquez sur "Installer" et attendez la fin du processus (~2–5 minutes). L’installation va :

1. Valider les données
2. Générer les secrets (SECRET_KEY Django, mot de passe Redis)
3. Télécharger les images Docker
4. Démarrer les conteneurs (web, frontend, redis, celery)
5. Exécuter les migrations de base de données
6. Importer les nomenclatures et référentiels
7. Créer le compte administrateur

#### 7. Accéder à l’application

Une fois l’installation terminée, accédez à :

```
http://votre-domaine:8080    (si Apache/Nginx)
https://votre-domaine        (si Traefik)
```

Connectez-vous avec l’email et le mot de passe administrateur définis à l’étape 5.

### Sans Apache/Nginx sur le serveur : Traefik (tout en un clic)

Si vous **ne cochez pas** « Un serveur Apache ou Nginx est-il déjà présent sur ce serveur ? » :

- Un conteneur **Traefik** est lancé avec les conteneurs Cicada.
- Traefik écoute sur les **ports 80 et 443** sur l’hôte.
- Il obtient et renouvelle automatiquement un certificat Let's Encrypt pour le domaine indiqué.
- Il redirige HTTP → HTTPS et route le trafic vers le frontend (Angular) et l’API (Django).
- L’accès se fait en **https://votre-domaine** (sans port dans l’URL).

Aucune configuration manuelle Apache/Nginx n’est nécessaire.

### Avec Apache ou Nginx déjà installé

Si vous **cochez** « Un serveur Apache ou Nginx est-il déjà présent sur ce serveur ? » :

- **Pas de Traefik.** Le frontend est exposé sur le port que vous avez indiqué (ex. 8080).
- Vous devez configurer un **virtual host dédié** sur votre Apache ou Nginx pour proxyfier le trafic vers ce port (ex. `ProxyPass / http://127.0.0.1:8080/` et `ProxyPass /api http://127.0.0.1:8000/`). Vous gérez vous-même le HTTPS (certificat Let's Encrypt avec certbot, CORS, etc.).

#### Exemple de configuration Apache

Activer les modules nécessaires :

```bash
sudo a2enmod proxy proxy_http proxy_wstunnel ssl headers
sudo systemctl reload apache2
```

Un seul virtual host sur le port 80 (à adapter : remplacer `cicada.example.org` par votre domaine, `8080`/`8000` par les ports indiqués lors de l’installation).

**Fichier** `/etc/apache2/sites-available/cicada.conf` :

```apache
<VirtualHost *:80>
    ServerName cicada.example.org

    ProxyPreserveHost On
    ProxyRequests Off

    # API Django (doit être avant la règle / pour priorité)
    ProxyPass /api http://127.0.0.1:8000/api
    ProxyPassReverse /api http://127.0.0.1:8000/api

    # Frontend Angular
    ProxyPass / http://127.0.0.1:8080/
    ProxyPassReverse / http://127.0.0.1:8080/
</VirtualHost>
```

Activer le site et recharger Apache :

```bash
sudo a2ensite cicada.conf
sudo systemctl reload apache2
```

Ensuite, exécutez **`sudo certbot --apache -d cicada.example.org`** pour générer le certificat Let's Encrypt et activer le HTTPS (port 443). Certbot ajoutera automatiquement le virtual host SSL.

### Test en local (sans DNS ni Let's Encrypt)

Pour tester sur votre machine sans domaine ni DNS :

1. **Cochez** « Un serveur Apache ou Nginx est-il déjà présent sur ce serveur ? » (ou considérez que vous testez sans reverse proxy).
2. Indiquez **Nom de domaine** : `localhost` (ou `127.0.0.1`) et **Port d’exposition du frontend** : `8080` (ou 80 si libre).
3. Une fois l’installation terminée, ouvrez **http://localhost:8080** (ou le port choisi).

Vous pouvez aussi utiliser un nom personnalisé via le fichier hosts : ajoutez par exemple `127.0.0.1 cicada.local` dans `/etc/hosts`, puis utilisez **Nom de domaine** = `cicada.local` et accédez à **http://cicada.local:8080**. Le trafic reste en HTTP, sans certificat.

## Configuration post-installation

### Modifier l'URL de l'API de suivi

Si nécessaire, vous pouvez modifier l'URL de l'API de suivi dans :

```bash
sudo nano /etc/cicada/cicada.conf
```

Puis redémarrer les services :

```bash
sudo systemctl restart cicada-installer
sudo systemctl restart cicada-heartbeat.timer
```

## Mise à jour

### Ce qui se passe automatiquement au démarrage

À chaque démarrage du conteneur `web`, l'entrypoint exécute automatiquement :

1. Attente que PostgreSQL et Redis soient disponibles
2. **`python manage.py migrate`** — applique toutes les nouvelles migrations de base de données
3. **`python manage.py collectstatic`** — met à jour les fichiers statiques
4. **`python manage.py check`** — vérifie la cohérence de la configuration Django
5. Lancement du serveur (gunicorn en production)

**Vous n'avez donc jamais besoin de lancer `migrate` ou `collectstatic` manuellement.** Un simple redémarrage de la stack suffit.

### Sauvegarde avant mise à jour (recommandé)

Avant toute mise à jour, sauvegardez la base de données :

```bash
# Si la base est dans Docker (DB_TYPE=docker)
docker compose --env-file /var/lib/cicada/.env exec db \
  pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backup_cicada_$(date +%Y%m%d).sql

# Si la base est externe (DB_TYPE=existing) — recommandé en production
sudo -u postgres pg_dump cicada > backup_cicada_$(date +%Y%m%d).sql
```

### Les 3 méthodes de mise à jour

| Méthode | Prérequis | Commandes à taper |
|---------|-----------|-------------------|
| **Option 1** — Interface web | API de suivi opérationnelle | Aucune (clic bouton) |
| **Option 2** — `apt install` | Accès SSH au serveur | Une seule commande |
| **Option 3** — Commandes manuelles | Accès SSH au serveur | 4 commandes |

### Option 1 : Mise à jour depuis l'interface web (clic bouton)

> **Prérequis** : L'API de suivi (`tracking.cicada.reserves-naturelles.org`) doit être opérationnelle. Si elle ne l'est pas, cette option n'est pas disponible — utilisez l'option 2 ou 3.

1. Accédez à `/admin/system/` dans l'interface Django (compte superuser).
2. Si une mise à jour est disponible (détectée par le heartbeat), cliquez sur **« Mettre à jour »**.
3. La mise à jour est effectuée automatiquement sur le serveur :
   - Un fichier « trigger » est créé ; le service systemd `cicada-updater.path` réagit immédiatement.
   - Le script `cicada-updater` (exécuté en root) :
     - met à jour le paquet via APT (`apt install cicada=<version>`),
     - met à jour `CICADA_VERSION` dans `/var/lib/cicada/.env`,
     - tire les nouvelles images Docker (`docker compose pull`) et redémarre la stack (`docker compose up -d`),
     - redémarre le service de l'installateur web.
4. Aucune commande manuelle sur le serveur n'est nécessaire. Rafraîchissez la page après quelques dizaines de secondes pour constater la nouvelle version.

En cas d'échec, consulter les logs : `sudo journalctl -u cicada-updater.service` ou `sudo cat /var/log/cicada/updater.log`.

### Option 2 : Mise à jour via `apt install` (recommandé)

C'est la méthode la plus simple en ligne de commande. Le script `postinst` du package fait tout automatiquement : mise à jour de `CICADA_VERSION` dans `.env`, téléchargement des nouvelles images Docker, et redémarrage de la stack.

```bash
sudo apt-get update
sudo apt-get install cicada=<version>   # ex: cicada=0.1.15
```

C'est tout. Le package :
1. Met à jour les fichiers sur disque (docker-compose, scripts)
2. Met à jour `CICADA_VERSION` dans `/var/lib/cicada/.env`
3. Tire les nouvelles images Docker (`docker compose pull`)
4. Redémarre la stack Docker (`docker compose up -d`)
5. Les migrations et le collectstatic s'appliquent automatiquement au démarrage

Si le pull ou le redémarrage échoue, le script affiche les commandes manuelles à lancer.

### Option 3 : Mise à jour manuelle (commandes détaillées)

Si `apt install` n'est pas disponible ou en cas de problème, voici la procédure complète étape par étape via SSH.

#### Étape 1 — Sauvegarde de la base de données

```bash
# Si la base est dans Docker (DB_TYPE=docker)
cd /usr/share/cicada
sudo docker compose --env-file /var/lib/cicada/.env exec db \
  pg_dump -U $(grep POSTGRES_USER /var/lib/cicada/.env | cut -d= -f2) \
  $(grep POSTGRES_DB /var/lib/cicada/.env | cut -d= -f2) \
  > backup_cicada_$(date +%Y%m%d_%H%M%S).sql

# Si la base est externe (DB_TYPE=existing)
pg_dump -h <host> -U <user> <db_name> > backup_cicada_$(date +%Y%m%d_%H%M%S).sql
```

#### Étape 2 — Mettre à jour le package Debian

```bash
sudo apt-get update
sudo apt-get install cicada=<version>   # ex: cicada=0.1.15
```

#### Étape 3 — Mettre à jour la version dans le .env

```bash
sudo sed -i 's/^CICADA_VERSION=.*/CICADA_VERSION=<version>/' /var/lib/cicada/.env

# Vérifier
grep CICADA_VERSION /var/lib/cicada/.env
```

#### Étape 4 — Tirer les nouvelles images Docker

```bash
cd /usr/share/cicada
sudo docker compose --env-file /var/lib/cicada/.env pull
```

#### Étape 5 — Redémarrer la stack

```bash
sudo docker compose --env-file /var/lib/cicada/.env down
sudo docker compose --env-file /var/lib/cicada/.env up -d
```

Au redémarrage, l'entrypoint applique automatiquement :
- `python manage.py migrate` (migrations de base de données)
- `python manage.py collectstatic` (fichiers statiques)
- `python manage.py check` (vérification Django)

#### Étape 6 — Vérifier les logs

```bash
sudo docker compose --env-file /var/lib/cicada/.env logs -f web
```

Attendez de voir dans les logs :
```
=== Application des migrations ===
  Applying plans.0036_remove_etat_actuel... OK
  ...
=== Initialisation terminée ===
```

Ctrl+C pour quitter les logs une fois l'initialisation terminée.

#### Étape 7 — Vérifier l'état des conteneurs

```bash
sudo docker compose --env-file /var/lib/cicada/.env ps
```

Tous les services doivent être à l'état `Up` ou `Up (healthy)`.

#### Étape 8 — Mettre à jour les nomenclatures (si nécessaire)

Si la nouvelle version ajoute ou modifie des nomenclatures (données de référence) :

```bash
sudo docker compose --env-file /var/lib/cicada/.env exec web \
  python manage.py import_nomenclatures --force
```

Consultez les notes de version (changelog) pour savoir si cette étape est requise. En cas de doute, la lancer ne pose aucun risque — elle met à jour les nomenclatures existantes et ajoute les nouvelles.

## Avertissements critiques — Ne pas perdre de données

### JAMAIS `docker compose down -v`

Le flag **`-v`** supprime les **volumes Docker**, c'est-à-dire :

| Volume | Contenu | Conséquence si supprimé |
|--------|---------|------------------------|
| `postgres_data` | **Toute la base de données** | Plans, utilisateurs, sites, enjeux — **TOUT est perdu** |
| `media_files` | Fichiers uploadés | Documents de plans, cartes, rapports — **perdus** |
| `redis_data` | Cache et tâches Celery | Tâches en cours perdues (moins critique) |
| `logs_data` | Historique des logs | Logs perdus (moins critique) |

**Commande sûre** : `docker compose down` (sans `-v`) — arrête les conteneurs mais **préserve toutes les données**.

### JAMAIS `seed_testdata` en production

```bash
# NE JAMAIS exécuter en production :
docker compose exec web python manage.py seed_testdata         # injecte de faux utilisateurs/plans/sites
docker compose exec web python manage.py seed_testdata --reset # SUPPRIME des données
```

### JAMAIS supprimer les volumes Docker manuellement

```bash
# NE JAMAIS exécuter :
docker volume rm cicada_postgres_data     # supprime la base de données
docker volume prune                       # supprime TOUS les volumes non utilisés
docker system prune -a --volumes          # supprime TOUT (images + volumes + cache)
```

### JAMAIS modifier ou supprimer les fichiers de migration

Les fichiers dans `migrations/` sont le versionnement de la base de données. Les supprimer ou les modifier après qu'ils ont été appliqués en production rend la base incohérente et peut entraîner des pertes de données.

## Désinstallation

```bash
sudo apt remove cicada
sudo apt purge cicada
```

**Attention** : La désinstallation ne supprime pas les conteneurs ni les volumes Docker. Pour tout arrêter et supprimer les conteneurs Cicada (y compris Traefik si vous l’aviez utilisé), voir la section *Nettoyer après des essais* ci‑dessous.

## Dépannage

### Nettoyer après des essais (conteneurs et ports)

Si des installations précédentes ont laissé des conteneurs ou des ports utilisés (erreur « port is already allocated », « orphan containers »), nettoyez ainsi :

```bash
cd /usr/share/cicada

# Arrêter et supprimer tous les conteneurs du projet (base + db + traefik)
# --remove-orphans supprime les conteneurs orphelins (ex. Traefik si vous avez réinstallé sans Traefik)
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.traefik.yml \
  --env-file /var/lib/cicada/.env down --remove-orphans
```

Si le fichier `.env` n’existe pas ou vous voulez forcer l’arrêt de tout ce qui porte le nom « cicada » :

```bash
# Lister les conteneurs Cicada
docker ps -a --filter "name=cicada"

# Tout arrêter et supprimer
docker rm -f $(docker ps -aq --filter "name=cicada") 2>/dev/null || true
```

Pour repartir de zéro (y compris la base de données et les volumes) :

```bash
cd /usr/share/cicada
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.traefik.yml \
  --env-file /var/lib/cicada/.env down -v --remove-orphans
```

Pour relancer le formulaire d’installation après un échec (sans désinstaller le package) :

```bash
sudo rm -f /var/lib/cicada/.install_lock
# Puis ouvrir à nouveau http://localhost:4567 (ou l’URL du serveur d’installation)
```

### Le serveur d'installation ne démarre pas

```bash
# Vérifier le statut du service
sudo systemctl status cicada-installer

# Voir les logs
sudo journalctl -u cicada-installer -f
```

### Les conteneurs Docker ne démarrent pas

```bash
# Vérifier les logs Docker
docker-compose -f /usr/share/cicada/docker-compose.yml logs

# Vérifier le fichier .env
cat /var/lib/cicada/.env
```

### Le heartbeat ne fonctionne pas

```bash
# Vérifier le timer
sudo systemctl status cicada-heartbeat.timer

# Voir les logs du heartbeat
sudo journalctl -u cicada-heartbeat.service -f

# Exécuter manuellement
sudo /usr/bin/cicada-heartbeat
```

## Tests de déploiement

Des scripts de test sont disponibles dans `packaging/` pour valider l'installation et la mise à jour avant un déploiement en production.

| Test | Environnement | Durée | Usage |
|------|--------------|-------|-------|
| Tests Docker (5 scripts) | Conteneur Docker | 30s - 10 min | Développement courant |
| **Test VM (Multipass)** | VM Ubuntu réelle | 10 - 20 min | **Avant une release** |

Les tests Docker vérifient l'installation des fichiers et services, mais ne peuvent pas tester le vrai flux d'upgrade (pas de systemd). Le test VM (Multipass) teste le flux complet : installation v1 → upgrade v2, avec systemd et Docker réels.

### Quand lancer ces tests

- **Tests Docker** : pendant le développement, pour vérifier que les fichiers du package sont corrects
- **Test VM** : **avant chaque publication d'un nouveau package `.deb`** (release). C'est le seul test qui valide le flux d'upgrade complet en conditions réelles.

### Pourquoi ces tests ne sont pas en CI (GitHub Actions)

1. **Hyperviseur requis** : le test VM utilise Multipass (KVM/QEMU), incompatible avec les runners GitHub Actions
2. **Durée** : 10-20 min par exécution, trop long pour un pipeline déclenché à chaque push
3. **Fréquence** : le packaging ne change qu'à chaque release, pas à chaque commit

Les tests applicatifs (pytest, Jest, Playwright) qui valident les migrations, les nomenclatures et la logique métier tournent déjà en CI à chaque push.

### Lancer le test d'upgrade

```bash
# Prérequis (une seule fois)
sudo snap install multipass

cd packaging

# Test complet (adapter les versions à la release en cours)
./test-upgrade-vm.sh --from 0.1.14 --to 0.1.15

# Relancer rapidement (réutilise la VM existante)
./test-upgrade-vm.sh --skip-install --from 0.1.14 --to 0.1.15

# Nettoyer après les tests
./test-upgrade-vm.sh --cleanup
```

Pour le détail complet des tests disponibles, voir [`packaging/TESTING.md`](../packaging/TESTING.md).

## Support

Pour toute question ou problème, consultez :
- La documentation : https://github.com/RNF-SI/Cicada
- Les issues GitHub : https://github.com/RNF-SI/Cicada/issues
