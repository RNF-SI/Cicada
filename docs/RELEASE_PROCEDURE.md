# Procédure de mise en production CICADA

Cette note décrit les étapes pour publier une nouvelle version : images Docker, package .deb et dépôt APT.

## Vue d’ensemble

- Les **images Docker** (backend, frontend) sont construites et poussées sur GHCR lors d’un **push de tag** `v*` (ex. `v0.1.13`) — voir `.github/workflows/docker-publish.yml`. Le tag est posé **sur `develop`** (cf. §2).
- Le **package .deb** est construit par la CI au **même moment** (workflow `.github/workflows/build-deb.yml`) : un seul tag déclenche images Docker + .deb avec la même version.
- Le **déploiement se fait aujourd’hui par installation directe du .deb** (`dpkg -i`), le dépôt APT étant hors service (cf. §4). C’est la voie décrite en §7.

## 1. Préparer la version

- Décider du numéro de version (ex. `0.1.21`).
- **`version.txt`** : doit être mis à jour manuellement — le versionnage est **manuel**, `release-please` est désynchronisé et son échec sur `main` est sans conséquence.
- **`packaging/debian/DEBIAN/control`** et **`packaging/debian/etc/cicada/cicada.conf`** : écrasés automatiquement par la CI lors du build .deb. Les mettre à jour est optionnel (utile uniquement pour les builds locaux).

## 2. Bumper la version et créer le tag

Le tag se pose **sur `develop`**, qui est la branche de référence des releases : c’est de là que sont sorties toutes les versions depuis la 0.1.31. Avancer `main` est facultatif et se fait après coup, en fast-forward.

```bash
git checkout develop
git pull

# Mettre à jour version.txt
echo "0.1.21" > version.txt
git add version.txt
git commit -m "chore: bump version 0.1.21"

# Créer et pousser le tag
git tag v0.1.21
git push origin develop && git push origin v0.1.21

# Facultatif : remettre main à niveau, sans merge commit ni divergence.
# La condition doit être vraie, sinon main a des commits que develop n'a pas —
# dans ce cas, ne pas forcer : traiter la divergence à part.
git merge-base --is-ancestor origin/main origin/develop && git push origin develop:main
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

> ⚠️ **Le dépôt APT est actuellement hors service** : `reprepro` n’est pas installé sur la machine qui l’héberge et la **clé GPG secrète de signature est absente** (seule la publique est présente). Cette section est conservée pour le jour où le dépôt sera rétabli ; en attendant, déployer par installation directe du `.deb` — voir **§7**.


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

## 5. Résumé du flux réel

| Étape | Action |
|-------|--------|
| 1 | Développement sur `develop`, CI verte. |
| 2 | Bumper `version.txt`, commiter, puis créer et pousser le tag `vX.Y.Z` **sur `develop`** → la CI construit les images Docker et le .deb. |
| 3 | Attendre que **Docker Build & Push** et **Build Debian package** soient verts (le workflow `Tests` rejoue aussi la suite sur le tag). |
| 4 | Télécharger l’artefact : `gh run download <run_id> -n cicada-deb-X.Y.Z`. |
| 5 | `scp` du .deb sur le serveur puis `sudo dpkg -i` — le `postinst` fait le reste (voir §7). |
| 6 | Vérifier les tags d’images et les logs de démarrage (voir §7.4). |

## 6. Variables utiles pour le build du .deb

- **VERSION** : doit être identique au tag des images Docker (ex. `0.1.13` pour le tag `v0.1.13`).
- **TRACKING_API_URL** : URL de l’API de suivi (injectée dans `cicada.conf`). En CI, la valeur par défaut du script ou du workflow peut être adaptée (ex. `https://tracking.cicada.reserves-naturelles.org/api`).

## 7. Déployer sur un serveur (staging ou production)

Le déploiement se fait par **installation directe du `.deb`**. Le `postinst` du paquet est autonome : il met à jour `CICADA_VERSION` dans l’environnement, puis lance `docker compose pull` et `up -d`. Il n’y a **rien à lancer à la main** ensuite.

### 7.1 Prérequis

- Accès SSH au serveur (identifiants dans `DEPLOY_SERVERS.md`, non versionné).
- Le paquet a déjà été installé une fois sur la machine (fichiers en place : compose dans `/usr/share/cicada`, environnement dans `/var/lib/cicada/.env`).
- Le staging embarque sa base PostGIS **en conteneur** ; la production utilise une base **externe**. C’est la seule différence de topologie : les fichiers compose combinés diffèrent, le flux de déploiement est identique.

### 7.2 Récupérer le .deb

```bash
# Sur votre machine : trouver le run du build déclenché par le tag
gh run list --workflow=build-deb.yml --limit=3

# Télécharger l'artefact (son nom porte la version)
gh run download <run_id> -n cicada-deb-X.Y.Z -D ~/cicada-releases
```

### 7.3 Installer sur le serveur

```bash
scp ~/cicada-releases/cicada_X.Y.Z_amd64.deb <user>@<serveur>:~/
ssh <user>@<serveur>
sudo dpkg -i cicada_X.Y.Z_amd64.deb
```

⚠️ **Prévenir les utilisateurs en production** : le redémarrage des conteneurs coupe le service 20 à 40 secondes.

### 7.4 Vérifications post-déploiement

Les commandes `docker` passent toutes par `sudo` (l’utilisateur de service n’est pas dans le groupe `docker`) et par les fichiers compose combinés. Un alias évite de les retaper — il n’est **pas persistant**, à redéfinir à chaque session SSH :

```bash
ccd='sudo docker compose -f /usr/share/cicada/docker-compose.yml \
  -f /usr/share/cicada/docker-compose.db.yml \
  -f /usr/share/cicada/docker-compose.frontend-ports.yml \
  --env-file /var/lib/cicada/.env'

$ccd ps                      # les images doivent porter le tag :X.Y.Z
$ccd logs web --tail=40      # attendre « === Initialisation terminée === »
grep CICADA_VERSION /var/lib/cicada/.env

curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/   # → 200
```

> **La version déployée ne se vérifie ni par `/api/health/`** (qui ne renvoie aucune version) **ni par la page « Informations système »** : celle-ci affiche `0.0.0`, parce que `version.txt` est à la racine du dépôt alors que le contexte de build Docker est `./backend` — le fichier n’existe donc pas dans l’image et le backend retombe sur sa valeur par défaut. Les tags d’images (`$ccd ps`) et `CICADA_VERSION` font foi.

Si la release introduit de nouvelles permissions ou de nouveaux groupes Django :

```bash
$ccd exec web python manage.py create_permissions
```

#### Mise à jour des libellés de nomenclatures (issue #268)

Si la release modifie des libellés ou définitions dans `backend/nomenclatures_data/` (fichiers `nomenclatures_inserts.sql` et `types_inserts.sql`), exécuter explicitement :

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py import_nomenclatures --force
```

**Pourquoi :** au démarrage du conteneur, `import_nomenclatures` est lancé sans `--force`. Si la base est déjà complètement peuplée (cas prod après une release), le script **skip** silencieusement et n'applique aucun `UPDATE`. Les libellés affichés dans l'UI restent dans leur version pré-correction.

**Sécurité :** la commande est idempotente grâce au `ON CONFLICT DO UPDATE` — safe à exécuter à chaque release. Coût : ~700 `UPDATE` (négligeable).

**Quand sauter cette étape :** uniquement si la release ne touche **aucun** fichier sous `backend/nomenclatures_data/`. En cas de doute, exécuter la commande.

> **Note :** une amélioration long terme (détection automatique par hash des fichiers SQL) est tracée dans l'issue #268.

### 7.5 Pièges courants

Les commandes de la colonne « Solution » supposent l’alias `ccd` défini en §7.4.

| Problème | Cause | Solution |
|----------|-------|----------|
| 503 sur `/api` | Le vhost Apache ne pointe pas au bon endroit | `/api` doit aller sur le **port du frontend** (`FRONTEND_PORT`, ex. 8080) : c’est le conteneur frontend qui proxifie `/api` vers le backend. Viser 8000 ne marche que si le backend est exposé sur l’hôte |
| Le port 80 est déjà pris / Apache ne démarre plus | `TRAEFIK_ENABLED=true` | Mettre `false` dans `/var/lib/cicada/.env` et utiliser le compose `frontend-ports` |
| `docker: permission denied` | L’utilisateur de service n’est pas dans le groupe `docker` | Toujours préfixer par `sudo` (l’alias `ccd` le fait) |
| 503 sur le frontend | Le port du frontend a changé | Vérifier `FRONTEND_PORT` dans `/var/lib/cicada/.env` et que Apache pointe vers le bon port |
| `DisallowedHost` dans les logs | Domaine absent de `ALLOWED_HOSTS` | Ajouter le domaine dans `.env` puis `$ccd up -d web` |
| CORS errors dans le navigateur | Domaine absent de `CORS_ALLOWED_ORIGINS` | Ajouter `https://votre-domaine` dans `.env` puis recréer le conteneur web |
| `password authentication failed` | Le conteneur web pointe vers le mauvais PostgreSQL | Vérifier `POSTGRES_HOST` et `POSTGRES_PORT` dans `.env` (ex. `172.17.0.1` et `5432` pour une base hôte) |
| `doit être le propriétaire de la fonction public.unaccent` | Extensions créées par `postgres`, pas par l'utilisateur applicatif | `sudo -u postgres psql -d cicada -c "ALTER FUNCTION public.unaccent(text) OWNER TO cicada_user;"` |
| Variables `.env` non prises en compte | `docker compose restart` ne relit pas le `.env` | Utiliser `$ccd up -d` (recrée le conteneur) |
| `No space left` pendant le `pull` | L’extraction demande plus de place que le disque n’en offre, même avec quelques Go libres (le backend pèse ~1,9 Go décompressé) | `$ccd down`, supprimer les anciennes images (`docker image rm`), `docker system prune -af`, puis tirer le backend **seul** avant de relancer |
| Référentiels vides (TaxRef, HabRef) | Imports non exécutés au premier démarrage | Voir section "Import des référentiels" dans `INSTALLATION_GUIDE.md` |

### 7.6 Configuration Apache rappel

Tout passe par le **port du frontend** : le conteneur frontend sert l’application **et** proxifie `/api` vers le backend. Rediriger `/api` directement sur 8000 suppose que le backend soit exposé sur l’hôte, ce qui n’est pas le cas dans la topologie `frontend-ports`.

```apache
# /etc/apache2/sites-enabled/cicada-prod-le-ssl.conf
<VirtualHost *:443>
    ServerName cicada.example.org
    ProxyPreserveHost On
    ProxyRequests Off

    # Frontend Angular (port défini par FRONTEND_PORT) — sert aussi /api
    ProxyPass / http://127.0.0.1:8080/
    ProxyPassReverse / http://127.0.0.1:8080/

    # ... certificats SSL ...
</VirtualHost>
```

Après toute modification : `sudo systemctl reload apache2`

## 8. En cas de release manuelle (sans tag)

Si vous publiez une version sans tag (ou sans CI) :

1. Construire les images Docker à la main, les tagger et les pousser vers GHCR avec la version choisie.
2. Construire le .deb avec `VERSION=X.Y.Z ./build-deb.sh`.
3. Suivre les étapes §4 pour la publication APT.
