# Guide d'installation CICADA

Ce guide s'adresse à la personne qui installe et administre un serveur CICADA. Il suit l'ordre de l'installation : les choix à faire **avant**, l'installation elle-même, puis l'exploitation (mises à jour, sauvegardes, dépannage).

> Vue d'ensemble des serveurs et de leurs liens (dépôt APT, API de suivi, hub, serveur de bases) : [INFRASTRUCTURE.md](INFRASTRUCTURE.md). Tests du paquet avant une release : [packaging/TESTING.md](../packaging/TESTING.md).

**Sommaire**

1. [Avant de commencer](#1-avant-de-commencer)
2. [Installer](#2-installer)
3. [Le formulaire, section par section](#3-le-formulaire-section-par-section)
4. [Publier le site derrière Apache ou Nginx](#4-publier-le-site-derrière-apache-ou-nginx)
5. [Premier accès et vérifications](#5-premier-accès-et-vérifications)
6. [Mettre à jour](#6-mettre-à-jour)
7. [Sauvegarder et restaurer](#7-sauvegarder-et-restaurer)
8. [Modifier la configuration](#8-modifier-la-configuration)
9. [Dépannage](#9-dépannage)
10. [Désinstaller](#10-désinstaller)
11. [Ce qu'il ne faut jamais faire](#11-ce-quil-ne-faut-jamais-faire)

---

## 1. Avant de commencer

### Le serveur

- **Debian 12+** ou **Ubuntu 22.04+**, en **amd64**, avec un accès root ou sudo. Debian 11 n'est pas prise en charge.
- Un accès Internet sortant : dépôts Docker et CICADA, images Docker.
- Un **nom de domaine** (ex. `cicada.mon-organisme.org`) dont la zone DNS pointe **déjà** vers ce serveur. Sans lui, pas de certificat HTTPS.

CICADA tourne entièrement dans des conteneurs Docker ; Docker est installé avec le paquet s'il manque.

### Trois choix à faire avant d'ouvrir le formulaire

| Choix | Options | Comment trancher |
|---|---|---|
| **Qui publie le site sur Internet ?** | **Traefik** (fourni par CICADA) ou **votre Apache/Nginx** | Si un Apache ou un Nginx tourne déjà sur le serveur (il occupe les ports 80 et 443), c'est lui : Traefik ne pourrait pas démarrer. Sinon, Traefik, qui gère seul le HTTPS. |
| **Où est la base de données ?** | **Dans Docker**, sur ce serveur, ou sur un **serveur PostgreSQL existant** | Dans Docker : rien à préparer, c'est le plus simple. Serveur existant : une commande à lancer en root **sur le serveur de base** (voir [§ 3.3](#33-base-de-données-postgresql)). PostgreSQL installé directement sur le serveur CICADA n'est pas pris en charge : utilisez la base dans Docker. |
| **Comment les utilisateurs se connectent ?** | **Comptes CICADA** (e-mail + mot de passe) ou **comptes GeoNature/UsersHub** | Un seul mode par instance. GeoNature/UsersHub demande GeoNature **2.17.0 minimum** (voir [§ 3.7](#37-mode-de-connexion)). |

### Installer CICADA sur un serveur qui héberge déjà GeoNature

C'est possible, sans rien changer à GeoNature (inutile de le « dockeriser ») : CICADA vit dans ses conteneurs, GeoNature reste tel qu'il est. Trois points d'attention :

- **Apache est déjà là** (c'est lui qui publie GeoNature) : choisissez « Apache/Nginx » dans le formulaire, et publiez CICADA par un **second virtual host** ([§ 4](#4-publier-le-site-derrière-apache-ou-nginx)).
- **Choisissez un port libre** pour CICADA : GeoNature et ses modules occupent déjà certains ports (8000 pour GeoNature, d'autres pour TaxHub, UsersHub, l'atlas…). Vérifiez avec `sudo ss -ltn`.
- **Ne recopiez pas le virtual host de GeoNature** : il contient une règle `/api` qui, dans celui de CICADA, enverrait l'application… vers GeoNature ([le piège #231](#le-piège-à-éviter-règle-api)).

Pour la base, la base dans Docker est la plus simple et ne touche pas au PostgreSQL de GeoNature. Utiliser ce dernier est possible ([§ 3.3](#33-base-de-données-postgresql)).

Un serveur à part reste plus confortable (les deux applications ne se disputent ni la mémoire ni les ports), mais rien ne l'impose.

---

## 2. Installer

### Une commande

```bash
curl -fsSL https://apt.cicada.reserves-naturelles.org/install.sh | sudo bash
```

Elle configure le dépôt Docker (s'il ne l'est pas déjà) et celui de CICADA avec sa clé de signature, installe le paquet `cicada`, puis affiche l'adresse du formulaire d'installation : **`http://votre-serveur:4567`**.

- Elle peut être relancée sans risque.
- Version précise : `… | sudo bash -s -- --version 0.1.55`.
- Système non reconnu (dérivé de Debian…) : `… | sudo bash -s -- --force`, à vos risques.
- Si le système propose de redémarrer des services (dbus, getty, systemd-logind), vous pouvez ignorer : ils sont sans rapport avec CICADA.

Le paquet apporte sa propre source APT et la clé du dépôt : les versions suivantes arriveront par `apt` et par le bouton de mise à jour de l'application, sans autre manipulation ([§ 6](#6-mettre-à-jour)).

<details>
<summary>Installation manuelle, sans le script</summary>

```bash
# Dépôt Docker
sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
. /etc/os-release
curl -fsSL "https://download.docker.com/linux/$ID/gpg" | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$ID $VERSION_CODENAME stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Dépôt CICADA
curl -fsSL https://apt.cicada.reserves-naturelles.org/cicada-repo-key.gpg \
  | sudo gpg --dearmor -o /usr/share/keyrings/cicada-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/cicada-archive-keyring.gpg] https://apt.cicada.reserves-naturelles.org stable main" \
  | sudo tee /etc/apt/sources.list.d/cicada.list

sudo apt-get update && sudo apt-get install cicada
```

Sans accès au dépôt CICADA, le paquet se télécharge depuis la [page des versions](https://github.com/RNF-SI/Cicada/releases) : `sudo apt install ./cicada_X.Y.Z_amd64.deb` (le dépôt Docker reste nécessaire).

</details>

### Ouvrir le formulaire

Dans un navigateur : **`http://votre-serveur:4567`**. Si la page ne répond pas : `sudo systemctl status cicada-installer` (et `sudo systemctl restart cicada-installer` s'il est arrêté).

Remplissez le formulaire ([§ 3](#3-le-formulaire-section-par-section)), puis cliquez sur **« Installer »**. Comptez **10 à 20 minutes** : l'installation vérifie la base, génère les secrets, télécharge les images, démarre les conteneurs, applique les migrations, importe les référentiels (nomenclatures, TaxRef, HabRef, INPG, CAMPanule, découpage administratif), crée le compte administrateur, enregistre l'instance auprès de l'API de suivi, puis redirige vers l'application.

---

## 3. Le formulaire, section par section

### 3.1 Compte administrateur

E-mail, mot de passe (8 caractères minimum, à confirmer), nom et prénom du premier **super administrateur**.

> En mode de connexion **GeoNature/UsersHub** ([§ 3.7](#37-mode-de-connexion)), ce compte ne peut pas se connecter par mot de passe : il faut un compte UsersHub portant **le même e-mail**. CICADA le reconnaît à la première connexion et lui conserve ses droits.

### 3.2 Configuration du site

**Nom de domaine** : sans `http://` (ex. `cicada.mon-organisme.org`).

**« Un serveur Apache ou Nginx est-il déjà présent sur ce serveur ? »**

| | Case **décochée** : Traefik | Case **cochée** : votre Apache/Nginx |
|---|---|---|
| Qui écoute sur 80/443 | Traefik (conteneur CICADA) | votre Apache/Nginx |
| HTTPS | automatique (Let's Encrypt) | à faire vous-même (certbot) |
| À renseigner | l'e-mail pour Let's Encrypt (par défaut celui de l'administrateur) | le **port d'exposition** du frontend (ex. `8080`, à choisir libre) et l'**adresse publique** du site |
| Après l'installation | rien | un virtual host ([§ 4](#4-publier-le-site-derrière-apache-ou-nginx)) |

L'**adresse publique** (mode Apache/Nginx) est celle que portent les liens des e-mails envoyés par CICADA :
- `https://domaine` (défaut) : votre Apache publie le site en HTTPS — le cas normal ;
- `http://domaine` : publié sans HTTPS ;
- `http://domaine:port` : pas de virtual host, on accède directement au port (essais uniquement).

Le champ **« Port backend »** peut être laissé à `8000` : l'application n'est jamais exposée directement sur l'hôte.

### 3.3 Base de données PostgreSQL

**Nouvelle base dans Docker** : choisissez un mot de passe (ou cliquez sur « Générer ») et laissez les autres valeurs. La base est créée par l'installation.

> ⚠️ Ce mot de passe est fixé à la **première** création de la base. Si vous relancez le formulaire après un échec, réutilisez le même (voir [§ 9](#relancer-le-formulaire-après-un-échec)).

**Serveur PostgreSQL existant** (serveur mutualisé, PostgreSQL de GeoNature…) :

*Prérequis sur le serveur de base* : PostgreSQL 15 ou plus avec le paquet PostGIS correspondant (ex. `postgresql-17-postgis-3`), à l'écoute du réseau (`listen_addresses` ne doit pas valoir `localhost`). Si ce n'est pas le cas, il faudra le modifier puis **redémarrer** PostgreSQL, ce qui coupe brièvement les autres applications : le script de préparation le détecte et s'arrête avant de rien changer, à vous de choisir le moment.

1. Saisissez l'**adresse du serveur de base telle que le serveur CICADA la joint**. Jamais `localhost` ni une adresse de la machine elle-même : vu de l'application, qui tourne dans un conteneur, `localhost` désigne le conteneur. Changez port, nom de base ou utilisateur si besoin.
2. Le formulaire affiche une commande à lancer **en root sur le serveur de base**, par exemple :

   ```bash
   curl -fsSL http://192.0.2.10:4567/prepare-db.sh | sudo bash -s -- --client 192.0.2.10
   ```

   Ce script, fourni par l'installateur (donc de la même version) :
   - crée le compte `cicada_user` (mot de passe généré et **affiché à la fin**) et la base `cicada` ;
   - active PostGIS et crée les schémas de CICADA ;
   - ajoute **une seule ligne** à `pg_hba.conf`, limitée à cette base, ce compte et l'adresse du serveur CICADA ;
   - **recharge** PostgreSQL sans le redémarrer : aucune coupure, aucune autre base touchée.

   Il peut être relancé sans risque ; le mot de passe d'un compte existant n'est alors **pas** changé (`--password` pour le redéfinir). Si vous avez changé port, nom de base ou utilisateur, la commande affichée en tient déjà compte. Aide : `bash prepare-db.sh --help`.
3. Reportez le **mot de passe affiché** dans le formulaire et cliquez sur **« Tester la connexion »**. Le test vérifie la connexion depuis le serveur CICADA, PostGIS et les schémas, et dit quoi corriger en cas d'échec. **L'installation ne démarre pas tant qu'il n'est pas vert.**

*Le serveur de base ne joint pas le serveur CICADA* (pare-feu) : téléchargez le script depuis un poste qui voit l'installateur (`http://<serveur-cicada>:4567/prepare-db.sh`), copiez-le sur le serveur de base et lancez `sudo bash prepare-db.sh --client <ip-du-serveur-cicada>`.

*Pourquoi une commande à part ?* Créer PostGIS exige un super-utilisateur PostgreSQL, et autoriser le serveur CICADA demande de modifier `pg_hba.conf` : deux opérations réservées à qui administre le serveur de base. Le formulaire n'a ainsi jamais besoin d'un compte super-utilisateur.

### 3.4 Redis

Rien à changer : Redis tourne dans Docker. Le mot de passe est généré s'il est laissé vide.

### 3.5 Serveur mail (SMTP)

Pour que CICADA envoie des e-mails (inscriptions, notifications, mot de passe oublié) : serveur, port, TLS, authentification et adresse d'expéditeur. Case décochée, les e-mails sont seulement écrits dans les journaux : utile pour un essai, pas pour une instance en service.

### 3.6 Exploration fédérée (optionnel)

Prépare le raccordement au **hub national**, qui permet de chercher dans les plans de toutes les structures participantes. Cocher la case **ne publie rien** : le partage s'active ensuite, par un super administrateur, dans *Administration > Paramètres*.

- **Identifiant de l'instance** : ⚠️ **définitif**. Minuscules, chiffres et tirets (ex. `cen-aura`). Il entre dans la référence publique de chaque plan.
- **Nom affiché** : ce que les autres structures voient comme provenance de vos plans.
- **URL du hub** : déjà renseignée (hub RNF). À ne changer que pour un hub de test.
- **Jetons** : laissez-les vides. L'adhésion se demande depuis *Administration > Paramètres* une fois l'installation terminée, et RNF la valide.
- **Relayer l'exploration** : décoché, l'exploration ne montre que vos propres plans.

Tout cela se règle aussi plus tard dans *Administration > Paramètres*.

### 3.7 Mode de connexion

- **Comptes CICADA** : chacun se connecte avec l'e-mail et le mot de passe de son compte CICADA (inscription et mot de passe oublié dans l'application).
- **Comptes GeoNature/UsersHub** (cas de RNF) : on se connecte **uniquement** avec son compte UsersHub ; le compte CICADA est créé à la première connexion et rattaché à son organisme UsersHub. GeoNature **2.17.0 minimum**. À renseigner :
  - l'**adresse de l'API GeoNature** (valeur `API_ENDPOINT` de sa configuration, souvent terminée par `/api`) ;
  - l'**identifiant de l'application CICADA dans UsersHub** ;
  - le **libellé** du bouton de connexion (ex. « Compte RNF ») ;
  - facultatif : les `id_organisme` UsersHub à ignorer (« Autre », comptes de test…).

### 3.8 Consentement RGPD (optionnel)

Le suivi technique (version, heartbeat quotidien) est anonyme et ne demande pas de consentement. Cocher la case transmet en plus aux mainteneurs le nom de la structure et un e-mail de contact, pour pouvoir vous prévenir (mise à jour de sécurité…).

---

## 4. Publier le site derrière Apache ou Nginx

*Uniquement si vous avez coché « Apache ou Nginx » ([§ 3.2](#32-configuration-du-site)). Avec Traefik, il n'y a rien à faire.*

Un **virtual host** dit à Apache : « les requêtes pour tel nom de domaine, envoie-les à tel endroit ». Celui de CICADA envoie **tout** le trafic de son domaine vers le port choisi dans le formulaire. Il cohabite avec les autres sites du serveur (GeoNature…) : Apache choisit le bon d'après le nom demandé.

```
Navigateur ──► Apache (80/443)
                 ├─ geonature.mon-organisme.org → GeoNature (inchangé)
                 └─ cicada.mon-organisme.org    → 127.0.0.1:8090 → conteneur frontend CICADA
                                                                     └─ /api → application (réseau Docker interne)
```

Dans les exemples : domaine `cicada.mon-organisme.org`, port `8090`. Remplacez-les par les vôtres.

**1. Modules Apache** (souvent déjà actifs) :

```bash
sudo a2enmod proxy proxy_http proxy_wstunnel ssl headers
```

**2. Le virtual host**, dans un fichier à lui — ne touchez pas à ceux des autres sites. `/etc/apache2/sites-available/cicada.conf` :

```apache
<VirtualHost *:80>
    ServerName cicada.mon-organisme.org

    ProxyPreserveHost On
    ProxyRequests Off

    # Tout passe par le conteneur frontend, qui transmet lui-même /api à l'application.
    ProxyPass / http://127.0.0.1:8090/
    ProxyPassReverse / http://127.0.0.1:8090/
</VirtualHost>
```

**3. Activer** (un `reload` ne coupe pas les autres sites) :

```bash
sudo a2ensite cicada.conf
sudo apache2ctl configtest      # doit répondre « Syntax OK »
sudo systemctl reload apache2
```

**4. HTTPS** (le domaine doit déjà pointer vers le serveur) :

```bash
sudo certbot --apache -d cicada.mon-organisme.org
```

Certbot crée le virtual host HTTPS (`cicada-le-ssl.conf`) en recopiant le précédent, et redirige HTTP vers HTTPS. Relisez-le : on ne doit y trouver que les deux lignes `ProxyPass /` et `ProxyPassReverse /`, plus les lignes de certificat.

**5. Vérifier** :

```bash
curl -i https://cicada.mon-organisme.org/api/health/
```

La réponse doit contenir un en-tête **`X-Correlation-ID`** : c'est la preuve que la requête est arrivée à CICADA.

### Le piège à éviter : règle `/api`

N'ajoutez **aucune** ligne `ProxyPass /api …` au virtual host de CICADA, même si celui de GeoNature en contient une. Le conteneur frontend s'occupe déjà de `/api`, et l'application n'est pas exposée sur l'hôte : une règle `/api` vers le port 8000 envoie les appels à **ce qui écoute sur le port 8000 de l'hôte** — sur un serveur GeoNature, GeoNature lui-même. La connexion à CICADA échoue alors en 404 (#231). Symptôme : pas d'en-tête `X-Correlation-ID` au test de l'étape 5.

### Remarques

- Le port du frontend reste joignable directement (`http://serveur:8090`), en contournant Apache. Fermez-le au pare-feu si le serveur est exposé.
- Avec Nginx, même principe : un bloc `server` dont la `location /` fait `proxy_pass http://127.0.0.1:8090;` avec `proxy_set_header Host $host;`.

---

## 5. Premier accès et vérifications

L'adresse de l'application :
- avec Traefik : `https://votre-domaine` ;
- avec Apache/Nginx : `https://votre-domaine` une fois le virtual host en place ([§ 4](#4-publier-le-site-derrière-apache-ou-nginx)), ou en attendant `http://votre-domaine:port`.

Connectez-vous avec le compte administrateur ([§ 3.1](#31-compte-administrateur)). Puis, dans *Administration* :
- **Paramètres** : textes d'accueil et logo de la structure, mesure d'audience, exploration fédérée ;
- **Organismes** et **Sites** : votre structure et ses espaces ;
- **Utilisateurs** : inviter ou valider les premiers comptes.

Les référentiels (nomenclatures, TaxRef, HabRef, INPG, CAMPanule, découpage administratif) sont importés au démarrage de l'application. Si une liste reste vide (espèces, habitats), voir [§ 9](#un-référentiel-est-vide).

---

## 6. Mettre à jour

### Ce qui se passe à chaque mise à jour

Le paquet met à jour la version dans `/var/lib/cicada/.env`, télécharge les nouvelles images et redémarre l'application (~30 s d'interruption). Au démarrage, l'application applique seule les migrations de la base, complète les référentiels et son index de recherche. **Il n'y a jamais de `migrate` à lancer à la main.**

Faites une [sauvegarde](#7-sauvegarder-et-restaurer) avant.

### Depuis l'application (recommandé)

*Administration > Mise à jour* (super administrateur) : quand une version plus récente est publiée, le bouton **« Mettre à jour »** lance la mise à jour sur le serveur, et la page en suit l'avancement. Elle est prévenue de la nouvelle version par le heartbeat quotidien.

En cas d'échec : `sudo journalctl -u cicada-updater.service` et `/var/log/cicada/updater.log`.

### En ligne de commande

```bash
sudo apt-get update
sudo apt-get install cicada            # dernière version
# ou une version précise :  sudo apt-get install cicada=0.1.55
```

C'est tout : le paquet fait le reste (version dans `.env`, images, redémarrage). En cas d'échec du téléchargement ou du redémarrage, il affiche les commandes à lancer.

### Garder la main sur le moment

Le dépôt CICADA étant une source APT comme les autres, un `sudo apt upgrade` de routine met aussi CICADA à jour. Pour l'éviter : `sudo apt-mark hold cicada`, puis `sudo apt-mark unhold cicada` avant une mise à jour voulue.

---

## 7. Sauvegarder et restaurer

Deux choses à sauvegarder : **la base** et **les fichiers déposés** (documents des plans, logos). Le reste (images, configuration générée) se reconstruit à la réinstallation, à l'exception de `/var/lib/cicada/.env`, à garder aussi.

### Base dans Docker

```bash
# Sauvegarde
sudo docker exec cicada_prod_db sh -c 'pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB"' \
  > cicada_$(date +%F).dump

# Restauration (application arrêtée pendant l'opération)
sudo docker stop cicada_prod_web cicada_prod_celery_worker cicada_prod_celery_beat
sudo docker exec -i cicada_prod_db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists' \
  < cicada_AAAA-MM-JJ.dump
sudo docker start cicada_prod_web cicada_prod_celery_worker cicada_prod_celery_beat
```

### Base sur un serveur PostgreSQL existant

Sur le **serveur de base** :

```bash
sudo -u postgres pg_dump -Fc cicada > cicada_$(date +%F).dump
# Restauration (application arrêtée sur le serveur CICADA, comme ci-dessus) :
sudo -u postgres pg_restore -d cicada --clean --if-exists cicada_AAAA-MM-JJ.dump
```

### Fichiers déposés

```bash
sudo docker run --rm -v cicada_media_files:/media -v "$PWD":/sauvegarde alpine \
  tar czf /sauvegarde/cicada_media_$(date +%F).tgz -C /media .
```

Planifiez ces commandes (cron) et copiez les fichiers hors du serveur.

---

## 8. Modifier la configuration

La configuration de l'instance est dans **`/var/lib/cicada/.env`** (lisible par root seulement). Après l'avoir modifiée, il faut recréer les conteneurs.

Les commandes `docker compose` de CICADA ont besoin de plusieurs fichiers, qui dépendent de vos choix (base dans Docker ou non, Traefik ou Apache). Plutôt que de les écrire à la main, définissez cette fonction dans votre session :

```bash
cicada_compose() {
  sudo bash -c '. /usr/share/cicada/compose-files.sh &&
    docker compose $(compose_files_args) --env-file /var/lib/cicada/.env "$@"' cicada_compose "$@"
}
```

Puis :

```bash
sudo nano /var/lib/cicada/.env
cicada_compose up -d            # recrée les conteneurs dont la configuration a changé
cicada_compose ps               # tous les services doivent être « Up » ou « Up (healthy) »
cicada_compose logs -f web      # journaux de l'application (Ctrl+C pour quitter)
```

> N'utilisez pas `docker compose` sans ces fichiers (`down` puis `up -d` depuis `/usr/share/cicada`, par exemple) : en mode Apache, le frontend perdrait son port et le site tomberait ; en mode Traefik, il ne serait plus routé.

La plupart des réglages fonctionnels (textes d'accueil, logo, mesure d'audience, exploration fédérée, raccordement au hub) ne sont **pas** dans ce fichier mais dans *Administration > Paramètres*, sans redémarrage.

`/etc/cicada/cicada.conf` porte l'adresse de l'API de suivi et du hub utilisées par le paquet (heartbeat, installateur). Vous n'avez normalement pas à y toucher.

---

## 9. Dépannage

### Le formulaire d'installation ne répond pas

```bash
sudo systemctl status cicada-installer
sudo journalctl -u cicada-installer -f
```

Après une installation réussie, le formulaire répond « Installation déjà effectuée » : c'est normal.

### Relancer le formulaire après un échec

Il suffit de rouvrir `http://votre-serveur:4567` : rien n'est verrouillé tant que l'installation n'a pas réussi.

Avec une **base dans Docker**, la base a pu être créée lors de la première tentative, avec le mot de passe saisi alors. Réutilisez **le même mot de passe**. Si vous l'avez perdu et que la base ne contient encore rien, supprimez-la avant de relancer :

```bash
cicada_compose down
sudo docker volume rm cicada_postgres_data
```

### Les conteneurs ne démarrent pas

```bash
cicada_compose ps
cicada_compose logs web
```

Erreur « port is already allocated » : le port choisi est pris par un autre service (`sudo ss -ltnp` dit lequel). En mode Traefik, c'est en général un Apache/Nginx sur 80/443 : réinstallez en mode « Apache/Nginx ».

### La connexion à CICADA échoue en 404 derrière Apache

Une règle `ProxyPass /api` envoie l'application ailleurs : voir [le piège #231](#le-piège-à-éviter-règle-api).

### Les liens des e-mails pointent vers `http://domaine:8080`

Instances installées en mode Apache/Nginx avant la version 0.1.56 : l'installateur enregistrait toujours l'adresse d'accès direct. Corrigez dans `/var/lib/cicada/.env` :

```
SITE_URL=https://cicada.mon-organisme.org
CORS_ALLOWED_ORIGINS=https://cicada.mon-organisme.org,http://cicada.mon-organisme.org:8080
```

puis `cicada_compose up -d`.

### Un référentiel est vide

Les imports tournent à chaque démarrage de l'application et sautent ce qui est déjà importé. S'ils ont échoué (journaux : `cicada_compose logs web | grep -i warn`), relancez-les :

```bash
sudo docker exec cicada_prod_web python manage.py import_nomenclatures
sudo docker exec cicada_prod_web python manage.py import_habref        # ~29 000 habitats
sudo docker exec cicada_prod_web python manage.py import_taxref        # ~700 000 taxons, plusieurs minutes
sudo docker exec cicada_prod_web python manage.py import_inpg
sudo docker exec cicada_prod_web python manage.py import_campanule
sudo docker exec cicada_prod_web python manage.py import_ref_geo
sudo docker exec cicada_prod_web python manage.py refresh_taxref_views
```

Base sur un serveur existant préparée **sans** le script de préparation : l'index de recherche sans accents de TaxRef ne peut pas être créé. Sur le serveur de base : `sudo -u postgres psql -d cicada -c "ALTER FUNCTION public.unaccent(text) OWNER TO cicada_user;"`, puis relancez `import_taxref`.

### Le heartbeat ne fonctionne pas

Envoyé chaque jour à 3 h ; c'est lui qui annonce les nouvelles versions.

```bash
sudo systemctl status cicada-heartbeat.timer
sudo journalctl -u cicada-heartbeat.service
sudo /usr/bin/cicada-heartbeat          # l'exécuter maintenant
```

---

## 10. Désinstaller

```bash
sudo apt remove cicada     # arrête et supprime les conteneurs ; garde les données
sudo apt purge cicada      # idem, et retire en plus la configuration du paquet
```

Ni l'un ni l'autre ne supprime **les données** : volumes Docker (base, fichiers déposés), `/var/lib/cicada/.env` et l'identité de l'instance (`/etc/cicada/instance_token`). Une réinstallation reprend donc l'instance existante — c'est voulu.

Pour **tout** effacer, définitivement (après une [sauvegarde](#7-sauvegarder-et-restaurer) si besoin) :

```bash
sudo apt purge cicada
sudo docker volume rm cicada_postgres_data cicada_media_files cicada_static_files cicada_redis_data cicada_traefik_letsencrypt 2>/dev/null
sudo rm -rf /var/lib/cicada /etc/cicada
```

---

## 11. Ce qu'il ne faut jamais faire

- **`docker compose down -v`**, `docker volume prune`, `docker system prune --volumes` : le `-v` et les `prune` suppriment les volumes, c'est-à-dire **la base de données** (base dans Docker) et **tous les documents déposés**. `down` sans `-v` est sans danger.
- **`seed_testdata`** en production : il injecte de faux utilisateurs, plans et sites, et son option `--reset` supprime des données.
- **Modifier ou supprimer des fichiers de migration** : la base deviendrait incohérente.
- **Supprimer `cicada_traefik_letsencrypt`** (mode Traefik) : les certificats seraient redemandés, et Let's Encrypt limite le nombre de demandes.

---

## Support

Questions et signalements : https://github.com/RNF-SI/Cicada/issues
