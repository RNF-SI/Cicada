# Documentation CICADA — par où commencer ?

La documentation de CICADA vit à **deux endroits** :

| Où | Pour qui | Comment la lire |
|----|----------|-----------------|
| **Site de documentation** (`documentation/`) | Utilisateurs, référents, administrateurs, exploitants, intégrateurs d'API | Sur chaque instance, lien « Aide » (`/aide/`). En local : `docker compose up docs` → http://localhost:8001 |
| **Ce dossier** (`docs/`) | Développeurs du projet | Sur GitHub ou dans l'éditeur |

Une information n'est écrite qu'à un seul endroit : les guides d'exploitation (installation, mise à jour, e-mail, hub…) ont rejoint le site (#743), les fichiers de ce dossier qui portaient leur nom n'en sont plus qu'un renvoi.

---

## Je veux…

### …utiliser CICADA

→ **Site de documentation, « Guide utilisateur »** : une notice par profil (utilisateur, référent d'un plan, administrateur d'organisme, administrateur d'instance), et un tableau « Je veux… » en page d'accueil.

### …installer ou exploiter une instance

→ **Site de documentation, « Administration technique »** :

| Je veux… | Page |
|----------|------|
| installer une instance | [Installation](../documentation/docs/administration/installation.md) |
| mettre à jour, sauvegarder, revenir en arrière | [Installation, §§ 6 et 7](../documentation/docs/administration/installation.md#6-mettre-à-jour) |
| comprendre qui parle à qui (serveurs, hub, dépôt APT) | [Infrastructure](../documentation/docs/administration/infrastructure.md) |
| publier une release | [Releases](../documentation/docs/administration/releases.md) |
| charger TaxRef, HabRef, passer à une nouvelle version de GestRef | [Référentiels](../documentation/docs/administration/referentiels.md) |
| brancher la connexion GeoNature / UsersHub | [Connexion GeoNature](../documentation/docs/administration/connexion-geonature.md) |
| configurer l'envoi d'e-mails, Matomo, le hub | [E-mail](../documentation/docs/administration/email.md), [Mesure d'audience](../documentation/docs/administration/mesure-audience.md), [Hub](../documentation/docs/administration/hub.md) |

### …brancher une application sur l'API

→ **Site de documentation, « API »** : [prise en main](../documentation/docs/api/prise-en-main.md), une page par domaine et la référence OpenAPI complète. L'API publique des métadonnées des plans : [API_PUBLIQUE_PLANS.md](API_PUBLIQUE_PLANS.md).

### …développer sur CICADA

Dans l'ordre :

1. **[README du dépôt](../README.md)** — lancer le projet en local, architecture en un schéma.
2. **[GUIDE_DEVELOPPEUR.md](GUIDE_DEVELOPPEUR.md)** — conventions, commandes du quotidien.
3. **[FONCTIONNALITES.md](FONCTIONNALITES.md)** — comment fonctionne chaque fonctionnalité : règles métier, modèles, fichiers.
4. **[CLAUDE.md](../CLAUDE.md)** — la référence la plus détaillée et la plus à jour, sujet par sujet (règles de calcul, droits, fédération…).

Puis selon le sujet :

| Je travaille sur… | Lire |
|-------------------|------|
| l'interface (couleurs, composants, accessibilité) | [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) — **obligatoire avant tout code frontend** |
| les tests | [TESTING.md](TESTING.md) |
| l'import Excel d'un plan | [IMPORT_PLANS_GUIDE.md](IMPORT_PLANS_GUIDE.md) |
| l'exploration et l'index de recherche | [RECHERCHE.md](RECHERCHE.md) |
| la fédération (deux instances + hub en local) | [MULTI_INSTANCE_LOCAL.md](MULTI_INSTANCE_LOCAL.md) |
| la chaîne de release (commits, versions, images) | [RELEASE_PIPELINE.md](RELEASE_PIPELINE.md) |
| une copie de données réelles en local | [PARALLEL_REALDATA_STACK.md](PARALLEL_REALDATA_STACK.md) |
| les valeurs des nomenclatures | [NOMENCLATURES_REFERENCE.md](NOMENCLATURES_REFERENCE.md) |

### …rédiger la notice Word

[NOTICE_UTILISATEUR.md](NOTICE_UTILISATEUR.md) est la source de la notice Word (conversion pandoc, filtre et modèle dans `notice/`). Le site de documentation en reprend le contenu.

---

## Le reste du dossier

| Fichier | Statut |
|---------|--------|
| `API_PLANS_GUIDE.md`, `API_USERS_GUIDE.md`, `API_ORGANISMES_SITES_GUIDE.md`, `API_ACTIVITY_GUIDE.md` | Guides d'API historiques, rédigés à la main. **La référence à jour est l'OpenAPI** du site de documentation, générée depuis le code (`scripts/export-openapi.sh`). |
| `GUIDE_CICADA_COMPLET.md` / `.docx`, `GUIDE_SAISIE_ET_NAVIGATION_PG.md` / `.docx` | Anciens guides d'utilisation (juin–juillet 2026), remplacés par la notice du site. Gardés pour l'historique. |
| `PRIVACY_POLICY.md` | Politique de confidentialité (les CGU de chaque instance se règlent dans *Administration › Paramètres*). |
| `CONNEXION_GEONATURE.md`, `DEPLOIEMENT_HUB.md`, `EMAIL_CONFIGURATION.md`, `INFRASTRUCTURE.md`, `INSTALLATION_GUIDE.md`, `MESURE_AUDIENCE.md`, `NOMENCLATURES.md`, `RELEASE_PROCEDURE.md` | Renvois vers le site de documentation (#743). |
| `analyses/` | Analyses ponctuelles (couverture de tests…). |
