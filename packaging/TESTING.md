# Guide de test du package CICADA

> **Voir aussi** : [Guide d'installation](../docs/INSTALLATION_GUIDE.md) (procédures de mise à jour) | [README packaging](README.md) (construction du package) | [Guide de test global](../docs/TESTING.md) (tests applicatifs)

## Vue d'ensemble des tests

Il existe deux catégories de tests pour le packaging :

| Catégorie | Environnement | Systemd | Docker réel | Teste l'upgrade | Quand l'utiliser |
|-----------|--------------|---------|-------------|-----------------|-----------------|
| **Tests Docker** (rapides) | Conteneur Docker | Non | Partiel | Non | Développement, CI |
| **Test VM** (complet) | VM Multipass | Oui | Oui | Oui | Avant une release |

### Tests Docker (conteneurs) — développement courant

Rapides (2-10 min), automatisables, mais limités : pas de vrai systemd, Docker-in-Docker partiel.

| Script | Durée | Ce qu'il teste |
|--------|-------|----------------|
| `test-install-quick.sh` | ~30s | Vérification des fichiers installés uniquement (pas de Docker) |
| `test-install.sh` | ~5 min | Installation complète + fichiers + services systemd + heartbeat |
| `test-install-full.sh` | ~10 min | Installation + démarrage systemd + interface web |
| `test-install-web.sh` | ~5 min | Interface web Flask accessible sur http://localhost:4567 |
| `test-install-web-full.sh` | ~10 min | Interface web + Docker fonctionnel (pull images GHCR) |

### Test VM (Multipass) — avant une release

Conditions proches de la production : vrai OS Ubuntu, vrai systemd, vrai Docker, vrai APT. Teste le flux complet d'upgrade d'une version à une autre.

| Script | Durée | Ce qu'il teste |
|--------|-------|----------------|
| `test-upgrade-vm.sh` | 10-20 min | Installation v1 → upgrade v2 (options 2 et 3 du guide) |

---

## Tests Docker (rapides)

### Prérequis

```bash
# Construire le package .deb
cd packaging
VERSION=0.1.13 ./build-deb.sh
```

### Test basique d'installation

Vérifie que tous les fichiers sont installés correctement et que les services systemd sont configurés :

```bash
./test-install.sh
```

- Crée un conteneur Docker Debian propre
- Installe le package
- Vérifie que tous les fichiers sont en place
- Vérifie la configuration des services systemd
- Affiche la configuration et le token généré

### Test complet avec interface web

```bash
./test-install-full.sh
```

- Crée un conteneur avec Docker-in-Docker
- Installe le package
- Démarre le service installer
- Teste l'accessibilité de l'interface web sur http://localhost:4567

**Note** : Nécessite que Docker soit accessible depuis le conteneur (via socket monté).

### Test de l'interface web avec Docker fonctionnel

```bash
./test-install-web.sh       # Interface web seule
./test-install-web-full.sh  # Interface web + pull des images GHCR
```

Ces scripts lancent un conteneur avec le **socket Docker monté**, installent le package et démarrent l'installateur Flask. Vous pouvez alors ouvrir **http://localhost:4567** dans le navigateur et tester le formulaire d'installation complet.

L'installateur va :
1. Générer le fichier `.env` avec les paramètres saisis
2. Faire `docker compose pull` (images `ghcr.io/rnf-si/cicada-*`)
3. Lancer `docker compose up -d`

**Prérequis** : accès réseau à **ghcr.io** (GitHub Container Registry) depuis la machine hôte (les commandes Docker s'exécutent côté hôte via le socket monté).

Si les images ne sont pas encore publiées sur GHCR (ex. branche de dev), le **pull échouera** — dans ce cas, les autres tests (`test-install-quick.sh`, `test-install.sh`) restent valides pour valider la structure du package.

### Tests manuels dans le conteneur

```bash
# Accéder au conteneur
docker exec -it cicada-test-install bash

# Vérifier les fichiers
cat /etc/cicada/instance_token
cat /etc/cicada/cicada.conf
ls -la /usr/bin/cicada-*

# Vérifier les services
systemctl status cicada-installer.service
systemctl status cicada-heartbeat.timer

# Tester le heartbeat (échouera si l'API n'est pas accessible, c'est normal)
/usr/bin/cicada-heartbeat

# Tester l'interface web
curl http://localhost:4567/api/health
```

### Nettoyage des conteneurs

```bash
docker rm -f cicada-test-install cicada-test-full cicada-test-web cicada-test-web-full cicada-test-quick
docker image prune -f
```

---

## Test VM — avant une release

### Prérequis

- **Multipass** installé : `sudo snap install multipass`
- **dpkg-deb** disponible (inclus dans Debian/Ubuntu)
- Uniquement en **local** (pas en GitHub Actions — Multipass nécessite un hyperviseur)

### Quand l'utiliser

Ce test est conçu pour être lancé **avant un déploiement en production**. Il vérifie que :
- Le `postinst` détecte correctement un upgrade (vs première installation)
- `CICADA_VERSION` est mis à jour dans le `.env`
- Les services systemd restent actifs après l'upgrade
- La configuration `docker compose` est valide
- Les commandes manuelles (option 3) fonctionnent

### Usage

```bash
cd packaging

# Test avec les versions par défaut (0.1.12 → 0.1.13)
./test-upgrade-vm.sh

# Versions spécifiques (adapter selon la release en cours)
./test-upgrade-vm.sh --from 0.1.13 --to 0.1.14

# Tester uniquement l'option 2 (apt install automatique)
./test-upgrade-vm.sh --from 0.1.13 --to 0.1.14 --test option2

# Tester uniquement l'option 3 (commandes manuelles)
./test-upgrade-vm.sh --from 0.1.13 --to 0.1.14 --test option3

# Relancer rapidement (réutiliser la VM existante)
./test-upgrade-vm.sh --skip-install --from 0.1.13 --to 0.1.14

# Nettoyer la VM après les tests
./test-upgrade-vm.sh --cleanup
```

### Ce que le script fait

1. **Construit** les 2 packages `.deb` (version FROM et version TO)
2. **Crée** une VM Ubuntu avec Multipass
3. **Installe** Docker dans la VM
4. **Installe** le package v1 (première installation)
5. **Simule** un environnement configuré (crée le `.env` comme le ferait l'installateur web)
6. **Teste Option 2** : `dpkg -i` du package v2 → vérifie que le `postinst` met à jour le `.env` et relance Docker
7. **Teste Option 3** : commandes manuelles (`sed`, `docker compose config`) → vérifie que la config est valide
8. **Affiche** un résumé PASS/FAIL

### Investigation en cas d'échec

```bash
# Accéder à la VM
multipass shell cicada-test-upgrade

# Fichiers utiles
cat /etc/cicada/cicada.conf          # Config du package
cat /var/lib/cicada/.env             # Config Docker (CICADA_VERSION)
ls /var/log/cicada/                  # Logs
systemctl status cicada-*            # Services

# Relancer le postinst manuellement
sudo dpkg -i /home/ubuntu/cicada_0.1.14.deb
```

### Limitations

- **Option 1** (clic bouton) n'est pas testée : nécessite l'API de suivi (`tracking.cicada.reserves-naturelles.org`) opérationnelle
- Le `docker compose pull` échouera si les images GHCR n'existent pas encore pour la version TO (c'est attendu — le test vérifie la logique du `postinst`, pas le pull réel)
- Le test ne lance pas l'application complète (pas de PostgreSQL, pas de Django) — il vérifie le mécanisme d'upgrade

---

## Checklist avant release

Avant de publier un nouveau package, vérifier :

- [ ] `VERSION=X.Y.Z ./build-deb.sh` se construit sans erreur
- [ ] `./test-install-quick.sh` — fichiers installés aux bons emplacements
- [ ] `./test-install.sh` — services systemd configurés, token généré
- [ ] `./test-upgrade-vm.sh --from <version_actuelle> --to <nouvelle_version>` — upgrade fonctionne
- [ ] Les images Docker `ghcr.io/rnf-si/cicada-backend:<version>` et `cicada-frontend:<version>` sont publiées
- [ ] Les notes de version (changelog) sont à jour

---

## Dépannage

### Le conteneur Docker ne démarre pas

```bash
docker ps    # Vérifier que Docker tourne
```

### Les services systemd ne fonctionnent pas (tests Docker)

Dans Docker, systemd ne fonctionne pas nativement. C'est une limitation connue des tests Docker — utilisez le test VM pour valider systemd.

### La VM Multipass ne démarre pas

```bash
multipass list                      # Voir les VMs existantes
multipass info cicada-test-upgrade  # Détails de la VM
multipass restart cicada-test-upgrade  # Redémarrer
multipass delete cicada-test-upgrade && multipass purge  # Supprimer et recréer
```

### L'interface web n'est pas accessible

```bash
# Dans le conteneur Docker
docker exec cicada-test-install cat /tmp/cicada-installer.log

# Dans la VM Multipass
multipass exec cicada-test-upgrade -- journalctl -u cicada-installer.service -n 50
```
