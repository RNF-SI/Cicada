# Guide de test du package CICADA

## Tests rapides (recommandé)

### Test basique d'installation

Ce test vérifie que tous les fichiers sont installés correctement et que les services systemd sont configurés :

```bash
cd packaging
./test-install.sh
```

Ce script :
- Crée un conteneur Docker Debian propre
- Installe le package
- Vérifie que tous les fichiers sont en place
- Vérifie la configuration des services systemd
- Affiche la configuration et le token généré

**Avantages** :
- Rapide (~2-3 minutes)
- Ne nécessite pas Docker fonctionnel dans le conteneur
- Teste l'essentiel de l'installation

### Test complet avec interface web

Pour tester l'interface d'installation web complète :

```bash
cd packaging
./test-install-full.sh
```

Ce script :
- Crée un conteneur avec Docker-in-Docker
- Installe le package
- Démarre le service installer
- Teste l'accessibilité de l'interface web sur http://localhost:4567

**Note** : Nécessite que Docker soit accessible depuis le conteneur (via socket monté).

## Tests manuels dans le conteneur

### Accéder au conteneur de test

```bash
docker exec -it cicada-test-install bash
```

### Vérifier les fichiers

```bash
# Token d'instance
cat /etc/cicada/instance_token

# Configuration
cat /etc/cicada/cicada.conf

# Scripts
ls -la /usr/bin/cicada-*

# Services
systemctl status cicada-installer.service
systemctl status cicada-heartbeat.timer
```

### Tester le script heartbeat

```bash
# Vérifier que le script est exécutable
python3 /usr/bin/cicada-heartbeat --help

# Tester l'exécution (échouera si l'API n'est pas accessible, c'est normal)
/usr/bin/cicada-heartbeat
```

### Tester l'interface d'installation

Si le service est démarré :

```bash
# Vérifier le statut
systemctl status cicada-installer.service

# Voir les logs
journalctl -u cicada-installer.service -f

# Tester l'API
curl http://localhost:4567/api/health
```

## Tests dans une VM locale

Pour un test encore plus proche de la production :

### Option 1 : Vagrant (recommandé)

Créez un fichier `Vagrantfile` :

```ruby
Vagrant.configure("2") do |config|
  config.vm.box = "debian/bullseye64"
  config.vm.network "forwarded_port", guest: 4567, host: 4567
  config.vm.provision "shell", inline: <<-SHELL
    apt-get update
    apt-get install -y docker.io docker-compose python3 python3-pip curl
  SHELL
end
```

Puis :

```bash
vagrant up
vagrant ssh
# Dans la VM :
sudo dpkg -i /vagrant/packaging/build/cicada_0.0.1_amd64.deb
```

### Option 2 : Multipass (Ubuntu)

```bash
multipass launch --name cicada-test
multipass mount . cicada-test:/home/ubuntu/cicada
multipass shell cicada-test
# Dans la VM :
sudo dpkg -i /home/ubuntu/cicada/packaging/build/cicada_0.0.1_amd64.deb
```

## Checklist de test

Avant de publier le package, vérifier :

- [ ] Le package se construit sans erreur
- [ ] Tous les fichiers sont installés aux bons emplacements
- [ ] Les services systemd sont activés
- [ ] Le token d'instance est généré
- [ ] La configuration est correcte
- [ ] L'interface web démarre (si test complet)
- [ ] Les scripts sont exécutables
- [ ] Les permissions sont correctes

## Nettoyage

Après les tests :

```bash
# Nettoyer les conteneurs de test
docker rm -f cicada-test-install cicada-test-full

# Nettoyer les images inutiles
docker image prune -f
```

## Dépannage

### Le conteneur ne démarre pas

Vérifiez que Docker est en cours d'exécution :
```bash
docker ps
```

### Les services systemd ne fonctionnent pas

Dans Docker, systemd nécessite des privilèges. Le script utilise `--privileged`, mais si ça ne fonctionne pas :

```bash
docker exec -it cicada-test-install bash
# Démarrer systemd manuellement
/lib/systemd/systemd --system-unit=basic.target &
```

### L'interface web n'est pas accessible

Vérifiez les logs :
```bash
docker exec cicada-test-install journalctl -u cicada-installer.service -n 50
```

Vérifiez que le port est bien mappé :
```bash
docker ps | grep cicada-test
```
