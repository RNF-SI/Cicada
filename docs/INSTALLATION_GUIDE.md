# Guide d'installation CICADA

## Installation via APT

### Prérequis

- Système d'exploitation : Debian 11+ ou Ubuntu 20.04+
- Docker et Docker Compose installés
- Accès root ou sudo

### Étapes d'installation

#### 1. Ajouter le repository APT

```bash
# Ajouter la clé GPG
curl -fsSL https://apt.cicada.example.org/cicada-repo-key.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cicada-archive-keyring.gpg

# Ajouter le repository
echo "deb [signed-by=/usr/share/keyrings/cicada-archive-keyring.gpg] https://apt.cicada.example.org stable main" | sudo tee /etc/apt/sources.list.d/cicada.list

# Mettre à jour la liste des packages
sudo apt update
```

#### 2. Installer CICADA

```bash
sudo apt install cicada
```

L'installation va :
- Installer les fichiers nécessaires
- Générer un token d'instance unique
- Démarrer le serveur d'installation web

#### 3. Accéder à l'interface d'installation

Ouvrez votre navigateur et accédez à :

```
http://localhost:4567
```

#### 4. Remplir le formulaire d'installation

Le formulaire vous demande :

- **Compte administrateur** : email, mot de passe, nom, prénom
- **Configuration du site** : nom de domaine, **présence d’Apache/Nginx** sur le serveur, puis selon le cas : port d’exposition du frontend ou email Let's Encrypt
- **Base de données PostgreSQL** : hôte, port, nom, utilisateur, mot de passe
- **Redis** : hôte, port, mot de passe (optionnel)
- **Consentement RGPD** (optionnel) : pour partager vos données nominatives avec les mainteneurs

**Question « Un serveur Apache ou Nginx est-il déjà présent sur ce serveur ? »**  
- **Si vous ne cochez pas** : Traefik est utilisé sur les ports 80 et 443 (HTTPS avec Let's Encrypt). Aucune configuration Apache/Nginx à prévoir.
- **Si vous cochez** : pas de Traefik. Le frontend est exposé sur un port que vous choisissez (ex. 8080). Vous devrez configurer un virtual host dédié sur votre Apache ou Nginx pour proxyfier le trafic vers ce port (et éventuellement `/api` vers le backend).

#### 5. Lancer l'installation

Cliquez sur "Installer" et attendez la fin du processus. L'installation va :

1. Valider les données
2. Générer les secrets (clés, mots de passe)
3. Configurer l'environnement Docker
4. Démarrer les conteneurs Docker
5. Créer le compte administrateur
6. Enregistrer l'instance auprès de l'API de suivi

#### 6. Accéder à l'application

Une fois l'installation terminée, vous serez redirigé vers l'URL de l'application (ex. `http://votre-domaine` si port 80, ou `http://votre-domaine:8080` si vous avez choisi le port 8080). Connectez-vous avec les identifiants administrateur que vous avez définis.

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

### Vérifier les mises à jour disponibles

Dans l'interface d'administration Django (`/admin/system/`), vous pouvez voir si une mise à jour est disponible (grâce au heartbeat qui interroge l'API de suivi).

### Mettre à jour (sans intervention manuelle)

1. Accédez à `/admin/system/` dans l'interface Django (compte superuser).
2. Si une mise à jour est disponible, cliquez sur **« Mettre à jour »**.
3. La mise à jour est alors effectuée automatiquement sur le serveur :
   - Un fichier « trigger » est créé ; le service systemd `cicada-updater.path` réagit immédiatement.
   - Le script `cicada-updater` (exécuté en root) :
     - met à jour le paquet via APT (`apt install cicada=<version>`),
     - met à jour `CICADA_VERSION` dans `/var/lib/cicada/.env`,
     - tire les nouvelles images Docker (`docker compose pull`) et redémarre la stack (`docker compose up -d`),
     - redémarre le service de l'installateur web.
4. Aucune commande manuelle sur le serveur n'est nécessaire. Vous pouvez rafraîchir la page après quelques dizaines de secondes pour constater la nouvelle version.

En cas d'échec, consulter les logs : `sudo journalctl -u cicada-updater.service` ou `sudo cat /var/log/cicada/updater.log`.

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

## Support

Pour toute question ou problème, consultez :
- La documentation : https://github.com/RNF-SI/Cicada
- Les issues GitHub : https://github.com/RNF-SI/Cicada/issues
