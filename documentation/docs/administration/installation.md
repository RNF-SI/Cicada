# Guide d'installation CICADA

Ce guide s'adresse à la personne qui installe et administre un serveur CICADA. Il suit l'ordre de l'installation : les choix à faire **avant**, l'installation elle-même, puis l'exploitation (mises à jour, sauvegardes, dépannage).

> Vue d'ensemble des serveurs et de leurs liens (dépôt APT, API de suivi, hub, serveur de bases) : [Infrastructure](infrastructure.md). Tests du paquet avant une release : [packaging/TESTING.md](https://github.com/RNF-SI/Cicada/blob/main/packaging/TESTING.md).

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
| **Où est la base de données ?** | **Dans Docker**, sur ce serveur, ou sur un **serveur PostgreSQL existant** | Dans Docker : rien à préparer, c'est le plus simple. Serveur existant : une commande à lancer en root **sur le serveur de base** (voir [§ 3.3](#33-base-de-données-postgresql)), y compris quand ce PostgreSQL est installé sur le serveur CICADA lui-même. |
| **Comment les utilisateurs se connectent ?** | **Comptes CICADA** (e-mail + mot de passe) ou **comptes GeoNature/UsersHub** | Un seul mode par instance. Les comptes UsersHub sont vérifiés **dans la base UsersHub** (droit sur l'application CICADA) : voir [§ 3.7](#37-mode-de-connexion). |

### Installer CICADA sur un serveur qui héberge déjà GeoNature

C'est possible, sans rien changer à GeoNature (inutile de le « dockeriser ») : CICADA vit dans ses conteneurs, GeoNature reste tel qu'il est. Trois points d'attention :

- **Apache est déjà là** (c'est lui qui publie GeoNature) : choisissez « Apache/Nginx » dans le formulaire, et publiez CICADA par un **second virtual host** ([§ 4](#4-publier-le-site-derrière-apache-ou-nginx)).
- **Choisissez un port libre** pour CICADA : GeoNature et ses modules occupent déjà certains ports (8000 pour GeoNature, d'autres pour TaxHub, UsersHub, l'atlas…). Vérifiez avec `sudo ss -ltn`.
- **Ne recopiez pas le virtual host de GeoNature** : il contient une règle `/api` qui, dans celui de CICADA, enverrait l'application… vers GeoNature ([le piège #231](#piege-regle-api)).

Pour la base, la base dans Docker est la plus simple et ne touche pas au PostgreSQL de GeoNature. Utiliser ce dernier est possible ([§ 3.3](#33-base-de-données-postgresql)).

Un serveur à part reste plus confortable (les deux applications ne se disputent ni la mémoire ni les ports), mais rien ne l'impose.

---

## 2. Installer

### Une commande

```bash
curl -fsSL https://apt.cicada.reserves-naturelles.org/install.sh | sudo bash
```

Elle configure le dépôt Docker (s'il ne l'est pas déjà) et celui de CICADA avec sa clé de signature, installe le paquet `cicada`, puis affiche l'adresse du formulaire d'installation, avec son **jeton** : **`http://votre-serveur:4567/?jeton=…`**.

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

Dans un navigateur, ouvrez **le lien affiché à la fin de l'installation du paquet** (`http://votre-serveur:4567/?jeton=…`). Le jeton est personnel : sans lui, l'installateur refuse tout (403) — il écoute sur le réseau, et quiconque l'atteindrait installerait sinon l'instance avec son propre compte administrateur. Lien perdu : `sudo cat /etc/cicada/installer_token`. Si la page ne répond pas : `sudo systemctl status cicada-installer` (et `sudo systemctl restart cicada-installer` s'il est arrêté).

Une fois l'instance installée, l'installateur s'arrête de lui-même (deux minutes après la fin) et n'est plus relancé par les mises à jour.

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

1. Saisissez l'**adresse du serveur de base telle que le serveur CICADA la joint** (une seule adresse), ou `localhost` si PostgreSQL est installé sur le serveur CICADA lui-même (voir [ci-dessous](#postgresql-sur-le-serveur-cicada)). Changez port, nom de base ou utilisateur si besoin.
2. Le formulaire affiche une commande à lancer **en root sur le serveur de base**, par exemple :

   ```bash
   curl -fsSL http://192.0.2.10:4567/prepare-db.sh | sudo bash -s -- --client 192.0.2.10
   ```

   Ce script, fourni par l'installateur (donc de la même version) :
   - crée le compte `cicada_user` (mot de passe généré et **affiché à la fin**) et la base `cicada` ;
   - active PostGIS et crée les schémas de CICADA ;
   - ajoute **une seule ligne** à `pg_hba.conf`, limitée à cette base, ce compte et l'adresse du serveur CICADA, en **`hostssl`** : PostgreSQL refuse alors toute connexion en clair (il doit avoir `ssl = on`, le script le vérifie et dit quoi changer ; réseau privé sûr seulement : `--sans-ssl`). L'installateur écrit en face `POSTGRES_SSLMODE=require` ;
   - **recharge** PostgreSQL sans le redémarrer : aucune coupure, aucune autre base touchée.

   Il peut être relancé sans risque ; le mot de passe d'un compte existant n'est alors **pas** changé (`--password` pour le redéfinir). Si vous avez changé port, nom de base ou utilisateur, la commande affichée en tient déjà compte. Aide : `bash prepare-db.sh --help`.
3. Reportez le **mot de passe affiché** dans le formulaire et cliquez sur **« Tester la connexion »**. Le test vérifie la connexion depuis le serveur CICADA, PostGIS et les schémas, et dit quoi corriger en cas d'échec. **L'installation ne démarre pas tant qu'il n'est pas vert.**

#### PostgreSQL installé sur le serveur CICADA lui-même {#postgresql-sur-le-serveur-cicada}

Cas courant sur un serveur qui héberge déjà GeoNature. Vu de l'application, qui tourne dans un conteneur, `localhost` désigne le conteneur : l'installateur écrit donc `POSTGRES_HOST=host.docker.internal`, nom par lequel les conteneurs joignent le serveur (pont Docker).

1. Hôte : `localhost`.
2. Sur ce même serveur, lancez la commande affichée :

   ```bash
   sudo cicada-prepare-db --docker-local
   ```

   Elle autorise les réseaux Docker (`172.16.0.0/12`) et les adresses du serveur lui-même (`samehost`, pour les vérifications faites depuis le serveur) au lieu d’une adresse de serveur distant, et vérifie que PostgreSQL écoute sur l'interface Docker. Si `listen_addresses` vaut `localhost`, mettez `listen_addresses = '*'` dans `postgresql.conf` et redémarrez PostgreSQL (coupure brève des autres applications), puis relancez la commande.
3. Mot de passe affiché, « Tester la connexion », installation : comme ci-dessus.

Si un **pare-feu** tourne sur le serveur (ufw, nftables…), il doit laisser passer le port de PostgreSQL depuis les conteneurs, par exemple `sudo ufw allow from 172.16.0.0/12 to any port 5432 proto tcp`. Le script le signale pour ufw ; c'est le seul point que le test du formulaire ne peut pas vérifier.

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
- **Comptes GeoNature/UsersHub** (cas de RNF) : on se connecte **uniquement** avec son compte UsersHub ; le compte CICADA est créé à la première connexion et rattaché à son organisme UsersHub. À renseigner dans tous les cas : le **libellé** du bouton de connexion (ex. « Compte RNF ») et, facultatif, les `id_organisme` UsersHub à ignorer (« Autre », comptes de test…). Les comptes sont vérifiés **dans la base UsersHub** : seuls les comptes qui ont un profil sur **l'application CICADA** dans UsersHub (directement ou par un groupe) entrent, quelle que soit la version de GeoNature. Renseigner l'hôte, le port et la base, puis lancer **sur le serveur de cette base** la commande affichée par le formulaire (`cicada-usershub-lecture`, comme `cicada-prepare-db` au § 3.4) : elle crée le compte de lecture, autorise ce serveur dans `pg_hba.conf` et affiche le mot de passe à reporter. Indiquer enfin le **code de l'application CICADA** (`code_application`) et cliquer sur « Tester la base UsersHub ». Base sur ce serveur (GeoNature installé à côté) : `localhost`, la commande devient `sudo cicada-usershub-lecture --docker-local --db <base>`. Détails : [Vérification par la base UsersHub](connexion-geonature.md#verification-par-la-base-usershub).

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

Ajoutez-y une ligne, pour que le navigateur ne revienne jamais en clair (et n'y envoie jamais la session) — module `headers` (`sudo a2enmod headers`) :

```apache
Header always set Strict-Transport-Security "max-age=31536000"
```

Si l'Apache d'entrée est sur ce même serveur, mettez aussi `FRONTEND_BIND=127.0.0.1` dans `/var/lib/cicada/.env` ([§ 8](#8-modifier-la-configuration)) : le port du frontend ne sera plus joignable depuis le réseau en contournant le HTTPS.

**5. Vérifier** :

```bash
curl -i https://cicada.mon-organisme.org/api/health/
```

La réponse doit contenir un en-tête **`X-Correlation-ID`** : c'est la preuve que la requête est arrivée à CICADA.

### Le piège à éviter : règle `/api` {#piege-regle-api}

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

Le bouton de l'application, `apt install cicada` et `dpkg -i` suivent **le même déroulé**, sans rien à lancer à la main (jamais de `migrate`) :

| Étape | Si elle échoue |
|---|---|
| 1. Contrôle de l'espace disque | mise à jour **annulée, rien n'a changé** |
| 2. Téléchargement des nouvelles images | mise à jour **annulée, rien n'a changé** (l'application tourne toujours) |
| 3. Arrêt de l'application — la coupure commence | — |
| 4. [Sauvegarde vérifiée](#7-sauvegarder-et-restaurer) de la base, des fichiers déposés et de la configuration | mise à jour annulée, application relancée telle quelle |
| 5. Passage à la nouvelle version : migrations de la base, référentiels, index de recherche | **retour automatique** à la version précédente, avec la base d'avant la mise à jour |
| 6. Vérification : l'application répond, le frontend et les tâches de fond tournent — du moins ceux qui tournaient avant : un service déjà en échec avant la mise à jour ne la fait pas défaire, il est signalé | idem |

Comptez quelques minutes de coupure (étapes 3 à 6). Les anciennes images sont ensuite supprimées, sauf celles de la version précédente.

Si le serveur redémarre en pleine mise à jour, elle est reprise au démarrage suivant (`cicada-reprise.service`) : retour à la version précédente depuis la sauvegarde d'origine.

### Depuis l'application (recommandé)

*Administration > Mise à jour* (super administrateur) : quand une version plus récente est publiée, le bouton **« Mettre à jour »** lance la mise à jour sur le serveur, et la page en suit l'avancement. Elle est prévenue de la nouvelle version par le heartbeat quotidien. Elle affiche aussi la dernière sauvegarde et, en cas d'échec, ce qui s'est passé (annulée, version précédente rétablie, ou application arrêtée).

### En ligne de commande

```bash
sudo cicada-update                     # état : versions, conteneurs, dernière mise à jour, sauvegardes
sudo cicada-update install             # dernière version du dépôt
sudo cicada-update install 0.1.70      # une version précise
```

`sudo apt-get install cicada` (ou `cicada=0.1.70`) fait la même chose.

### Garder la main sur le moment

Le dépôt CICADA étant une source APT comme les autres, un `sudo apt upgrade` de routine met aussi CICADA à jour. Pour l'éviter : `sudo apt-mark hold cicada`, puis `sudo apt-mark unhold cicada` avant une mise à jour voulue.

### Une mise à jour s'est mal passée {#maj-mal-passee}

Tout se fait **sur le serveur**, sans l'application (qui peut ne plus répondre). Commencez toujours par :

```bash
sudo cicada-update status
```

Il dit la version du paquet, la version **en service**, l'état des conteneurs, l'issue de la dernière mise à jour avec sa cause, la sauvegarde prise avant, et le journal du conteneur en échec (`/var/log/cicada/maj-…-cicada_prod_web.log`). Journal complet : `/var/log/cicada/updater.log`.

| La dernière mise à jour… | Situation | Que faire |
|---|---|---|
| **annulée** | rien n'a changé, l'application tourne dans sa version | corriger la cause (réseau, espace disque : `sudo docker image prune -a`), puis `sudo cicada-update retry` |
| **échec — retour à la version précédente effectué** | l'application tourne dans sa version précédente, avec les données d'avant la mise à jour | lire la cause, la signaler (journal du conteneur joint) ; une fois corrigée — souvent par une version suivante — `sudo cicada-update retry` ou `sudo cicada-update install` |
| **ÉCHEC — application arrêtée** | le retour arrière n'a pas pu aller au bout (base injoignable…) ; la sauvegarde est intacte | corriger la cause, puis `sudo cicada-update rollback` : il reprend le retour arrière là où il s'est arrêté |
| **en cours ou interrompue** | serveur redémarré, commande coupée | `sudo cicada-update resume` (fait automatiquement au démarrage) |

Après un échec, le paquet installé est plus récent que la version en service : c'est voulu. L'application continue de proposer la mise à jour, et `retry` la relance. Une simple reconfiguration du paquet (`dpkg --configure -a`) ne retente **jamais** d'elle-même une mise à jour qui a échoué.

**Revenir en arrière après une mise à jour réussie** (un problème découvert ensuite) :

```bash
sudo cicada-update rollback --oui
```

La version précédente revient avec la base sauvegardée **juste avant** la mise à jour : tout ce qui a été saisi depuis est perdu (la commande le rappelle et attend `--oui`). Pour garder les saisies, préférez attendre une version corrective. La page *Administration › Mise à jour* ne présente pas ce retour comme un échec, et propose de nouveau la mise à jour.

**Revenir à une version plus ancienne que la précédente** : voir [§ 7](#revenir-version-ancienne).

??? note "Première mise à jour vers une version qui apporte ces protections"
    Elle est lancée par le service de mise à jour de la version précédente. En cas d'échec, le retour arrière se fait quand même ; ce service signale alors l'échec du paquet (« dpkg returned an error code »), et le paquet reste à configurer : `sudo dpkg --configure -a` le termine, sans nouvelle tentative.

---

## 7. Sauvegarder et restaurer

### Ce qui est sauvegardé, et quand

Une sauvegarde contient **la base** (celle que l'application utilise réellement, dans Docker ou sur un PostgreSQL existant), **les fichiers déposés** (documents des plans, logos) et **la configuration** (`/var/lib/cicada/.env`). Elle est **vérifiée** : l'archive de la base est relue en entier, chaque fichier a son empreinte, et le nombre de lignes de chaque table est noté.

Elle est faite **chaque nuit** vers 0 h 45 (`cicada-backup.timer`) et **avant chaque mise à jour**. Les sauvegardes sont dans `/var/backups/cicada/`, un dossier par sauvegarde, lisible par root seulement.

| Réglage (`/var/lib/cicada/.env`) | Défaut | Rôle |
|---|---|---|
| `CICADA_SAUVEGARDES_A_GARDER` | `5` | nombre de sauvegardes conservées (celle de la dernière mise à jour l'est toujours) |
| `CICADA_SAUVEGARDE_DOSSIER` | `/var/backups/cicada` | dossier des sauvegardes (par ex. un disque monté) |
| `CICADA_MAJ_ESPACE_MIN_GO` | `5` | espace libre exigé pour les images avant une mise à jour |
| `CICADA_MAJ_DELAI_DEMARRAGE` | `1800` | secondes laissées à l'application pour démarrer après une mise à jour |

!!! warning "Copiez les sauvegardes hors du serveur"
    Elles protègent d'une mise à jour ratée ou d'une erreur de manipulation, pas de la perte du serveur. Copiez régulièrement `/var/backups/cicada/` ailleurs (rsync, outil de sauvegarde de votre structure).

### Commandes

```bash
sudo cicada-backup                         # sauvegarde maintenant (base, fichiers, configuration)
sudo cicada-backup --sans-fichiers         # base et configuration seulement
sudo cicada-backup --liste                 # sauvegardes disponibles
sudo cicada-backup --verifier NOM          # relire une sauvegarde (empreintes, archive entière)

sudo cicada-restore NOM                    # explique ce qui sera remplacé
sudo cicada-restore NOM --oui              # restaure la base, relance l'application
sudo cicada-restore NOM --fichiers --oui   # la base et les fichiers déposés
```

La restauration est **tout ou rien** : elle se fait dans une seule transaction, avec le compte de l'application (aucun super-utilisateur, donc aussi sur un PostgreSQL existant), et le nombre de lignes de chaque table est contrôlé avant de valider. Une archive abîmée ou un manque de droits laissent la base telle qu'elle était. L'application est arrêtée pendant l'opération puis relancée.

Une sauvegarde d'une version **plus récente** que celle en service est refusée (l'application ne saurait pas lire cette base) ; une sauvegarde plus ancienne est mise à niveau par les migrations au redémarrage. `sudo cicada-backup --liste` indique la version de chaque sauvegarde.

### Revenir à une version plus ancienne {#revenir-version-ancienne}

`cicada-update rollback` ne revient qu'à la version d'avant la **dernière** mise à jour. Pour remettre l'instance dans une version plus ancienne (un défaut découvert plusieurs versions après sa livraison), repartez d'une **sauvegarde faite dans cette version** :

```bash
sudo cicada-backup --liste                                   # repérer une sauvegarde de la version voulue
sudo cicada-restore NOM --avec-sa-version                    # explique ce qui va changer
sudo cicada-restore NOM --avec-sa-version --oui              # version et base de la sauvegarde
sudo cicada-restore NOM --avec-sa-version --fichiers --oui   # … et ses fichiers déposés
```

Une ancienne version ne sait pas lire une base migrée depuis (tables et colonnes ajoutées) : la seule façon sûre d'y revenir est de reprendre **sa** base. **Tout ce qui a été saisi depuis la sauvegarde est perdu**. Défaire les migrations ne le sauverait pas : une migration de données ne se défait pas, et retirer une colonne efface son contenu.

Le déroulé est celui d'une mise à jour, avec les mêmes protections :

1. **Contrôles**, puis téléchargement des images de la version. Si elles manquent, rien n'a changé et l'application n'a pas été arrêtée.
2. Arrêt de l'application, puis **sauvegarde de l'état actuel**.
3. Restauration de la base de la sauvegarde (tout ou rien), passage à sa version avec **ses** fichiers de déploiement (conservés dans chaque sauvegarde), démarrage vérifié.
4. En cas d'échec, retour automatique à la version et à la base d'avant. Si le serveur redémarre en cours de route, la reprise se fait au démarrage.

La configuration actuelle (`/var/lib/cicada/.env`) est gardée, seule `CICADA_VERSION` change ; la configuration de l'époque reste lisible dans le fichier `env` de la sauvegarde.

Ensuite :

- `sudo cicada-update rollback --oui` défait ce retour : la version et la base d'avant reviennent ;
- le paquet installé reste plus récent que la version en service. L'application propose de nouveau la mise à jour, que le bouton ou `sudo cicada-update retry` relance quand la cause est corrigée. Les données de la sauvegarde sont alors mises à niveau par les migrations.

Une sauvegarde qui ne contient pas les fichiers de déploiement (faite par une version qui ne les gardait pas encore) reste utilisable tant que le serveur garde ceux de sa version, c'est-à-dire pour les cinq dernières versions installées. Sinon, la commande le dit et ne change rien.

### Serveur perdu : repartir d'une sauvegarde

Sur un nouveau serveur : installer CICADA ([§ 2](#2-installer)) avec une base vide, puis copier le dossier de sauvegarde dans `/var/backups/cicada/` et :

```bash
sudo cicada-restore NOM --avec-sa-version --fichiers --oui
```

L'instance repasse dans la version de la sauvegarde, même si le dépôt n'en propose plus qu'une plus récente. Si la sauvegarde a été faite dans la version installée, `sudo cicada-restore NOM --fichiers --oui` suffit.

Le fichier `env` de la sauvegarde contient l'ancienne configuration (secrets, adresse du hub, jetons) : reprenez-en ce qui doit l'être dans `/var/lib/cicada/.env`, puis `cicada_compose up -d` ([§ 8](#8-modifier-la-configuration)). Copiez aussi `/etc/cicada/instance_token` de l'ancien serveur si vous l'avez : c'est l'identité de l'instance auprès du serveur de suivi.

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

Trois réglages de sécurité y figurent, à vérifier sur une instance installée avant leur arrivée :

| Variable | Rôle | Valeur |
|---|---|---|
| `NUM_PROXIES` | nombre de proxys devant Django, pour lire l'adresse réelle du client (limite des essais de connexion). Faux, la limite saute ou s'applique à tout le monde à la fois | `2` derrière Apache / Nginx (défaut), `1` avec Traefik seul |
| `POSTGRES_SSLMODE` | chiffrement de la connexion à la base | `require` pour une base sur un autre serveur ; vide pour la base Docker |
| `FRONTEND_BIND` | interface où le port du frontend est publié | `127.0.0.1` si l'Apache / Nginx d'entrée est sur ce serveur : le port ne contourne plus le proxy (ni son HTTPS) depuis le réseau |

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

Il suffit de rouvrir le lien de l'installateur (avec son jeton, `sudo cat /etc/cicada/installer_token`) : rien n'est verrouillé tant que l'installation n'a pas réussi.

Si le fichier `/var/lib/cicada/.env` a disparu alors qu'une base Docker existe encore, l'installateur **refuse** de recommencer : il tirerait un nouveau mot de passe, qui ne correspond plus à la base, et une nouvelle `SECRET_KEY`, qui rend illisibles les secrets chiffrés en base. Restaurez le `.env` depuis sa copie (§ 7).

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

Une règle `ProxyPass /api` envoie l'application ailleurs : voir [le piège #231](#piege-regle-api).

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

Ni l'un ni l'autre ne supprime **les données** : volumes Docker (base, fichiers déposés), `/var/lib/cicada/.env`, l'identité de l'instance (`/etc/cicada/instance_token`) et les sauvegardes (`/var/backups/cicada`). Une réinstallation reprend donc l'instance existante — c'est voulu.

Pour **tout** effacer, définitivement (après une [sauvegarde](#7-sauvegarder-et-restaurer) si besoin) :

```bash
sudo apt purge cicada
sudo docker volume rm cicada_postgres_data cicada_media_files cicada_static_files cicada_redis_data cicada_traefik_letsencrypt 2>/dev/null
sudo rm -rf /var/lib/cicada /etc/cicada /var/backups/cicada
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
