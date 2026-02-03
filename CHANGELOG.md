# Changelog

## [0.1.8](https://github.com/RNF-SI/Cicada/compare/v0.1.7...v0.1.8) (2026-02-03)


### Bug Fixes

* **docker:** ajouter labels OCI pour lier les images GHCR au repo ([4dd0d4c](https://github.com/RNF-SI/Cicada/commit/4dd0d4c66bc4363f42f5fb26b1ff98e9d637b4be))
* **docker:** corriger les permissions des volumes en production ([d12b7f6](https://github.com/RNF-SI/Cicada/commit/d12b7f613f877b4a835708eeb52ce5b06d80313e))

## [0.1.7](https://github.com/RNF-SI/Cicada/compare/v0.1.6...v0.1.7) (2026-02-02)


### Features

* **docker:** supporter le build local dans docker-compose.prod.yml ([e092eca](https://github.com/RNF-SI/Cicada/commit/e092eca68eaf7067503cb829fdd4e95ed45e4bdc))
* **docker:** supporter le build local dans docker-compose.prod.yml ([e829ead](https://github.com/RNF-SI/Cicada/commit/e829eadf783a63d82012a5000806789881619631))

## [0.1.6](https://github.com/RNF-SI/Cicada/compare/v0.1.5...v0.1.6) (2026-02-02)


### Bug Fixes

* **deploy:** utiliser les variables d'environnement pour le superutilisateur ([4ebfe02](https://github.com/RNF-SI/Cicada/commit/4ebfe02ecf2ae2b2877050551408f18fff1569b2))
* **frontend:** autoriser tous les hosts pour le dev server Angular ([0a339c5](https://github.com/RNF-SI/Cicada/commit/0a339c5ecb02dd7d88e1716525083dbdb3bec731))

## [0.1.5](https://github.com/RNF-SI/Cicada/compare/v0.1.4...v0.1.5) (2026-02-02)


### Bug Fixes

* **docker:** retirer apache2-mod-rewrite du frontend Dockerfile ([383fb13](https://github.com/RNF-SI/Cicada/commit/383fb136f69b68867d380e414827dcaa3fd77ff1))
* **settings:** utiliser la variable d'environnement ALLOWED_HOSTS en développement ([69b5895](https://github.com/RNF-SI/Cicada/commit/69b5895f310018f225463c7eac21c8deeb2dfce8))

## [0.1.4](https://github.com/RNF-SI/Cicada/compare/v0.1.3...v0.1.4) (2026-02-02)


### Bug Fixes

* **docker:** ajouter build-essential pour compiler GDAL dans Dockerfi… ([e797555](https://github.com/RNF-SI/Cicada/commit/e7975552548dd9a4188889902db7730ce12ba302))
* **docker:** ajouter build-essential pour compiler GDAL dans Dockerfile.prod ([7a8c9e2](https://github.com/RNF-SI/Cicada/commit/7a8c9e2e18e9b28ec32186cf572c8c7e937c1aac))

## [0.1.3](https://github.com/RNF-SI/Cicada/compare/v0.1.2...v0.1.3) (2026-02-02)


### Bug Fixes

* **ci:** utiliser un PAT pour release-please ([3e12332](https://github.com/RNF-SI/Cicada/commit/3e12332ee34c87d568823d62f097438f60557d09))
* **ci:** utiliser un PAT pour release-please ([d3d2120](https://github.com/RNF-SI/Cicada/commit/d3d2120fce84870b1fe6c1bdf8d7e7d5a1ee8180))

## [0.1.2](https://github.com/RNF-SI/Cicada/compare/v0.1.1...v0.1.2) (2026-02-02)


### Bug Fixes

* **ci:** declencher docker-publish sur push tag au lieu de release event ([a27fa25](https://github.com/RNF-SI/Cicada/commit/a27fa25b1f34451eaf3fcadb2a7ca02fb365254e))
* **ci:** declencher docker-publish sur push tag au lieu de release event ([e92d572](https://github.com/RNF-SI/Cicada/commit/e92d5724a58b6b731ff4d8a2815080fbe60802d8))

## [0.1.1](https://github.com/RNF-SI/Cicada/compare/v0.1.0...v0.1.1) (2026-02-02)


### Features

* Acces admin pour les referents site et plan ([0ac0c21](https://github.com/RNF-SI/Cicada/commit/0ac0c21bb31e326b0258367ae052749830808438))
* **activity:** ajout onglet Mes droits sur la page Activité ([97f28a5](https://github.com/RNF-SI/Cicada/commit/97f28a5065b7c120747b723c0c0d5ff733f9a0de))
* add Docker configuration and project structure for issue [#7](https://github.com/RNF-SI/Cicada/issues/7) ([1841556](https://github.com/RNF-SI/Cicada/commit/1841556feb8686207155a368023a1af7d472af18))
* **admin-sites:** gestion multiple utilisateurs et organismes par site ([013d362](https://github.com/RNF-SI/Cicada/commit/013d362c69cedf1c933303ccd277a75f4ca39835))
* **admin:** Ajout colonne Plans de gestion dans la liste des utilisateurs ([23be621](https://github.com/RNF-SI/Cicada/commit/23be6211ec9ecfc226410189a642a7dff0b44142))
* **admin:** Gestion des accès aux modules (super_admin) ([6e4a8d6](https://github.com/RNF-SI/Cicada/commit/6e4a8d61b677d529af311be032ff6c3b24170047))
* **admin:** module administration (organismes, sites) ([6794f79](https://github.com/RNF-SI/Cicada/commit/6794f79bed94eaa24ad7f50a559047a30b597853))
* **admin:** refonte modal gestion sites-organismes ([d6255b8](https://github.com/RNF-SI/Cicada/commit/d6255b87e53c79ae24f32d60d898fbea401f991d))
* **admin:** refonte modal gestion users-organismes ([1089c77](https://github.com/RNF-SI/Cicada/commit/1089c7765b504eca2a528ddd6741daf8dd20a23e))
* **admin:** refonte modale gestion des sites utilisateurs ([b391a3b](https://github.com/RNF-SI/Cicada/commit/b391a3b25a12c6af78a35296e7fb67130e784600))
* Ajout de l'inscription publique avec workflow de validation ([82403d4](https://github.com/RNF-SI/Cicada/commit/82403d4b6f48e270a2718bc9cb255384b4e4ea50))
* ajouter configuration du site et page exploration ([c27c0ff](https://github.com/RNF-SI/Cicada/commit/c27c0ff9faf027fba2742f155dfe008707db7bdb))
* **api:** endpoint sites disponibles pour assignation ([60b8b41](https://github.com/RNF-SI/Cicada/commit/60b8b4138d0beb4067abc39099ebcf2bb68a8684))
* **auth:** login par email ou identifiant ([c58394f](https://github.com/RNF-SI/Cicada/commit/c58394f161fbcb8bf64d4368a70701d9203ba7a3))
* **auth:** système authentification JWT + page login ([b188450](https://github.com/RNF-SI/Cicada/commit/b18845029bf715d88e9f4f966714b69675de5540))
* **backend:** Ajout des champs de désactivation et validation utilisateur ([9c6668e](https://github.com/RNF-SI/Cicada/commit/9c6668ec7e2b08991892a08e782e37536719a3f4))
* **backend:** Ajout du système de notifications et demandes de validation ([a7969e7](https://github.com/RNF-SI/Cicada/commit/a7969e71ac9123ca1dd72bcfaccbecea638b00c4))
* **backend:** API endpoints pour demande d'accès module ([d440656](https://github.com/RNF-SI/Cicada/commit/d440656e525d11665782d3e6a0e341d6e9dc383f))
* **backend:** Endpoint statistiques publiques ([0a2280d](https://github.com/RNF-SI/Cicada/commit/0a2280d9d29d3418c8bfc33020a62d2165e78cde))
* **core:** ajout cd_nomenclature + commande seed_testdata ([4a081a5](https://github.com/RNF-SI/Cicada/commit/4a081a5b79d6a4a59244035f61b3cc191dd15857))
* **core:** Services et modèles pour gestion accès modules ([704e352](https://github.com/RNF-SI/Cicada/commit/704e352edf1c532aa8d20caddf6db4196e2123a8))
* **email:** tests d'intégration email avec Mailpit ([97cc6ef](https://github.com/RNF-SI/Cicada/commit/97cc6ef10612ce5fc8322a251531116fb616552e))
* **frontend:** Ajout de la page d'administration des validations ([401ea1c](https://github.com/RNF-SI/Cicada/commit/401ea1c343b8ad64bda1266424a7d718e127ee63))
* **frontend:** Ajout de la page profil et du composant cloche de notifications ([838e62c](https://github.com/RNF-SI/Cicada/commit/838e62c117e093aaf4a0f2d1ce8af97bad70fb8f))
* **frontend:** Services, modeles et traductions sites ([ade38b8](https://github.com/RNF-SI/Cicada/commit/ade38b8dbdd3d881f68997dc4ae628ed1a11cf73))
* **home:** Affichage dynamique des modules selon accès utilisateur ([e5767b5](https://github.com/RNF-SI/Cicada/commit/e5767b5a730129d4082913dd195d53a7587376f1))
* **i18n:** Traductions et routes pour gestion accès modules ([f78b98f](https://github.com/RNF-SI/Cicada/commit/f78b98fd46b7a9303ed9416596ba0a64aba8e767))
* implement complete REST API for organizations and sites with GeoJSON support [#16](https://github.com/RNF-SI/Cicada/issues/16) ([15afed6](https://github.com/RNF-SI/Cicada/commit/15afed65ba3f937de31c31150bb87451fd0775b8))
* implement complete REST API for user management [#15](https://github.com/RNF-SI/Cicada/issues/15) ([e8401c8](https://github.com/RNF-SI/Cicada/commit/e8401c80758d9f0c5dfe0006b658fb3944bafcdd))
* implement comprehensive role-based permissions system [#12](https://github.com/RNF-SI/Cicada/issues/12) ([c6f58e9](https://github.com/RNF-SI/Cicada/commit/c6f58e9b3695f6bb4e8c56e6ccc45720a09de78d))
* implement JWT authentication system [#10](https://github.com/RNF-SI/Cicada/issues/10) ([775bb08](https://github.com/RNF-SI/Cicada/commit/775bb085ca1eb51a315001fd99b2107b8edd18d5))
* implement management plans data models and admin interface [#18](https://github.com/RNF-SI/Cicada/issues/18) ([b5dd152](https://github.com/RNF-SI/Cicada/commit/b5dd152db3f929439d8f7e12b5e7019e3104cfeb))
* implement user and site data models [#14](https://github.com/RNF-SI/Cicada/issues/14) ([70c4491](https://github.com/RNF-SI/Cicada/commit/70c4491d64a9dc227df94f816581531d43f6708b))
* Initialisation du projet Angular 19 avec design system optimisé ([0077725](https://github.com/RNF-SI/Cicada/commit/007772539f03368528195ab4e724c616ab6fad41))
* Intégration des nomenclatures standardisées ([#40](https://github.com/RNF-SI/Cicada/issues/40)) ([9e50db0](https://github.com/RNF-SI/Cicada/commit/9e50db0c4207bb10d88e0bc85203d59d999f5b43))
* **invite:** invitations directes par les référents sans validation ([99615bd](https://github.com/RNF-SI/Cicada/commit/99615bd65badd9be99a045166073dcbc0013c290))
* **logging:** Système de logs production-ready avec correlation ID ([a21dcd9](https://github.com/RNF-SI/Cicada/commit/a21dcd94794164ad96acef4b0b85f7b99f6dfea2))
* **maps:** Ajout composants Leaflet pour cartographie ([f024e0e](https://github.com/RNF-SI/Cicada/commit/f024e0e3058ac77c705a1e884659b39ef02bdc88))
* **modules:** API REST centralisée pour la gestion des modules ([779c4d3](https://github.com/RNF-SI/Cicada/commit/779c4d386db78aabc63bf0ff381d14c707d47fb4))
* **my-requests:** Page Mes demandes avec demande d'accès modules ([bdac751](https://github.com/RNF-SI/Cicada/commit/bdac75158f5c61473b2ade654581c56697b19532))
* **plans:** ajout du modèle CorRolePlan pour liaison utilisateurs-plans ([38918e8](https://github.com/RNF-SI/Cicada/commit/38918e8129372206d9b878c0633132861868a4e6))
* **plans:** amélioration design bannière et positionnement tabs ([9de7a3d](https://github.com/RNF-SI/Cicada/commit/9de7a3d726ffd165b89d949b6b391b3e9b9edd0e))
* **plans:** amélioration design page détail plan selon Figma ([46704f7](https://github.com/RNF-SI/Cicada/commit/46704f75eaa74a8973cf936b474682443da59153))
* **plans:** amélioration liste des plans avec filtrage par scope ([c2ec510](https://github.com/RNF-SI/Cicada/commit/c2ec5109df9509b6279ac7af72539a7279789e42))
* **plans:** formulaire de création et gestion des sites en attente ([d19e8e0](https://github.com/RNF-SI/Cicada/commit/d19e8e05fb84825245832129cd50100de58560e6))
* **plans:** liste et détail des plans de gestion ([b8c1544](https://github.com/RNF-SI/Cicada/commit/b8c1544321a6756ebc07e963aa780e6b06dcffd5))
* **plans:** redesign page synthèse selon maquette Figma ([65fd058](https://github.com/RNF-SI/Cicada/commit/65fd058b51da8f5156ae7e8be3a369f297894dcd))
* **seed:** Ajout demandes d'accès module dans les données de test ([fee21ea](https://github.com/RNF-SI/Cicada/commit/fee21ea64fd3abae3e3eb485df0427bf773206bc))
* **seeders:** mise à jour des données de test pour plans et utilisateurs ([12df772](https://github.com/RNF-SI/Cicada/commit/12df772f26a5380193b8aeaac7ee067b48af4e14))
* **settings:** ajouter option de positionnement vertical de l'image ([616bea5](https://github.com/RNF-SI/Cicada/commit/616bea518d3548bcab0cc963a474351b2be52eac))
* **shared:** modales formulaires (organisme, site, liens) ([ba4af16](https://github.com/RNF-SI/Cicada/commit/ba4af1644190d0f38449b96715adf4e07b44be85))
* **sites:** Ajout demandes d'acces et devenir referent ([140cf99](https://github.com/RNF-SI/Cicada/commit/140cf99fd1f4a5b1924b496f08cff625b1bbd6b5))
* **sites:** Ajout du module sites avec authentification requise ([7b0879e](https://github.com/RNF-SI/Cicada/commit/7b0879e32d0cb7bfe67c843418ee8a674cb8c704))
* **sites:** améliorer la bannière selon le design Figma ([13a1f20](https://github.com/RNF-SI/Cicada/commit/13a1f20b5853a38549f8e0e1551099b1ab2870b9))
* **sites:** demandes de lien organisme-site et détection des demandes en attente ([3509bb3](https://github.com/RNF-SI/Cicada/commit/3509bb3ffa7087737dc777f0cfca200563914926))
* **sites:** import en masse de sites depuis GeoJSON/CSV ([af8f8fa](https://github.com/RNF-SI/Cicada/commit/af8f8fa725654b8cec13c0cfadce41de30c802d2))
* **sites:** Refonte complete du module sites ([768a68d](https://github.com/RNF-SI/Cicada/commit/768a68d73500488a7b76ec60b4b98a281aed0987))
* **sites:** utiliser des slugs au lieu des IDs dans les URLs ([aa9dcb0](https://github.com/RNF-SI/Cicada/commit/aa9dcb0b2e613a9ee4af6834c6b30964947c2c16))
* **validations:** ajouter demande de validation pour retrait site-organisme ([2200a39](https://github.com/RNF-SI/Cicada/commit/2200a39caf2c1527867294b1979d2a03a45d4314))
* **validations:** bloquer approbation site_access si site_org_link en attente ([c200ab5](https://github.com/RNF-SI/Cicada/commit/c200ab558d62cbf4cbb243fcdd577530e7ce20bc))


### Bug Fixes

* **admin:** affichage type de site ([7a1a6d5](https://github.com/RNF-SI/Cicada/commit/7a1a6d5836583419f24bd235d9643bf701b778fc))
* **admin:** Augmenter la taille des  tableaux admin ([073e4a4](https://github.com/RNF-SI/Cicada/commit/073e4a4da17407f5dbbd07f62a155792a1ed19de))
* **admin:** mapping user modales + CRUD sites ([fe2ef32](https://github.com/RNF-SI/Cicada/commit/fe2ef321bbbf018aa862c7757cf5ead7725ae9e9))
* afficher le nombre de plans dans la colonne Plans de l'admin sites ([e8a7b99](https://github.com/RNF-SI/Cicada/commit/e8a7b99b2f665b7bed500acd71454ddbe5b18d7a))
* **api:** correction suppression site d'un organisme ([4ea2087](https://github.com/RNF-SI/Cicada/commit/4ea2087b00f208d60d7d368b48826f3a177ed0ba))
* **backend:** servir les fichiers media en mode développement ([84fa6c9](https://github.com/RNF-SI/Cicada/commit/84fa6c91fff0149be1de5a3428c20f44898aaa62))
* Corrections diverses et ameliorations ([c031dfc](https://github.com/RNF-SI/Cicada/commit/c031dfccc99b80fe4294dc433266377813d6195e))
* **db:** empêcher suppression des sites au redémarrage ([89bb252](https://github.com/RNF-SI/Cicada/commit/89bb2526a06a3e81378491d7de3aa129f7c886aa))
* désactiver signaux users.signals pendant seed_testdata --reset ([8a7dc16](https://github.com/RNF-SI/Cicada/commit/8a7dc16e640ef88e45d3b01381d18f1ade5490a0))
* double tooltip et fermeture modales sur navigation ([59160cf](https://github.com/RNF-SI/Cicada/commit/59160cf7985f1bbbc2a7a97d194468358a597182))
* filtrage 'Mes sites' + seed_data super_admin lié à RNF ([165a6e0](https://github.com/RNF-SI/Cicada/commit/165a6e0a193222212dfb31c0405312712a7c3912))
* **home:** ajuster les dimensions de la vue invité selon Figma ([f827533](https://github.com/RNF-SI/Cicada/commit/f8275337ae6600614c51333be68a23a7d5d4b47a))
* **home:** Masquer les modules pour les utilisateurs non connectés ([8b108d3](https://github.com/RNF-SI/Cicada/commit/8b108d3c0db72629ec65d369ab0f3f6f5267e19f))
* **home:** mettre l'image en dessous du contenu sur la page d'accueil ([425a5f1](https://github.com/RNF-SI/Cicada/commit/425a5f1bbe96939db4d8cb69ef375574077ece20))
* **invite:** permettre aux référents de rechercher tous les organismes pour invitation ([6523230](https://github.com/RNF-SI/Cicada/commit/652323008656d4cdaa1860f99bb3fcaafcd35aca))
* **notifications:** éviter les notifications en double lors des validations ([0ad953d](https://github.com/RNF-SI/Cicada/commit/0ad953de2989f6bfb925bc4abb7d835da2d95886))
* **profile:** empêcher les super_admin de demander la suppression de compte ([e9a96ee](https://github.com/RNF-SI/Cicada/commit/e9a96ee1abea4a1bdb48c8f48127af3ad86b1722))
* retirer champ 'Principal' du modal de liaison site-organisme ([dbee35f](https://github.com/RNF-SI/Cicada/commit/dbee35f426eeaefdca392a4a86adb8be135a3d28))
* **security:** retirer les données sensibles avant passage en open-source ([45fe597](https://github.com/RNF-SI/Cicada/commit/45fe59779684f86790ad07bf0d129e0428e2c9ed))
* **settings:** ajouter homepage_image_position au fallback catchError ([c270647](https://github.com/RNF-SI/Cicada/commit/c270647695ffffdb99233a9f50b86b1a212eefbf))
* **settings:** changer la position par défaut de l'image à 'top' ([7cb43d7](https://github.com/RNF-SI/Cicada/commit/7cb43d7336d7b2c731098e8214134b8e05c8068f))
* **settings:** corriger les URLs des images pour le proxy frontend ([87bfaaa](https://github.com/RNF-SI/Cicada/commit/87bfaaa01a56cde5b4ee20fe8d2573ba48b48f7e))
* **sites:** aligner les boutons site-detail sur le design Figma ([5bffe0d](https://github.com/RNF-SI/Cicada/commit/5bffe0d448baf094a2eee380568f588b0cfcb2c8))
* **sites:** badges status avec fond blanc selon design Figma ([e0b2aff](https://github.com/RNF-SI/Cicada/commit/e0b2affbc2f98177e4c25137291fb51bb3cc19af))
* **sites:** boutons secondaires avec fond blanc sur bannière sombre ([354b903](https://github.com/RNF-SI/Cicada/commit/354b90335f0cdb9b76e0a19a66e7d62f48b4901f))
* **sites:** corriger erreur DELETE lors du retrait d'un utilisateur ([cec8acf](https://github.com/RNF-SI/Cicada/commit/cec8acfe55b56ab72165263f7aa7629c919c6aad))
* **sites:** corriger la taille de police des boutons de bannière ([8c8190c](https://github.com/RNF-SI/Cicada/commit/8c8190c68cfdb127b195353dbf88676b79ff9ef8))
* **sites:** corriger les lignes de la bannière et largeur du pattern ([3611f22](https://github.com/RNF-SI/Cicada/commit/3611f2219a1ce514a8f0329ea2288b9e820fffff))
* **sites:** lignes du breadcrumb entourent le texte (haut et bas) ([80af3ae](https://github.com/RNF-SI/Cicada/commit/80af3ae27f13942c7c87abc67b3d2cf6287ec65b))
* **sites:** positionner le texte du breadcrumb à gauche ([94d029e](https://github.com/RNF-SI/Cicada/commit/94d029e595ce38c3109a1eede08336800ab7e471))
* **sites:** refaire le breadcrumb selon le design Figma ([43fd4fe](https://github.com/RNF-SI/Cicada/commit/43fd4fee53cea675706beed8b5cf256011fa4acb))
* **sites:** remettre les lignes horizontales dans la bannière ([ced9b91](https://github.com/RNF-SI/Cicada/commit/ced9b912a45881f987e69788857abf25099320a8))
* **sites:** repositionner les lignes et le texte du breadcrumb ([c759d54](https://github.com/RNF-SI/Cicada/commit/c759d5458572a1f4c56653666b6743a75e27c425))
* **sites:** supprimer ancien CSS du séparateur dans responsive ([713fc29](https://github.com/RNF-SI/Cicada/commit/713fc29769caf63cb1f033e5d7c6f914b46b2376))
* **sites:** utiliser icône Flaticon pour le séparateur breadcrumb ([750b311](https://github.com/RNF-SI/Cicada/commit/750b31195f49456f58eb4d23faec5f17e88ca256))
* **sites:** utiliser un seul caractère flèche › dans le breadcrumb ([a66cfcf](https://github.com/RNF-SI/Cicada/commit/a66cfcf131e10ea570d57a9b976807fddf404dfc))
* **styles:** réduire taille SCSS sites et ajuster budget composant ([fc0bb4c](https://github.com/RNF-SI/Cicada/commit/fc0bb4c09349d455d51cded1aef252aed089138c))
* **tests:** convertir les tests bulk-import de Jasmine vers Jest ([bde8779](https://github.com/RNF-SI/Cicada/commit/bde8779273e64d33300daa0af573ce6030c8b618))
* **tests:** corriger test doublon nom dans bulk import ([d5caa09](https://github.com/RNF-SI/Cicada/commit/d5caa0915a11120078e795f685bbc79578ed6b35))
* **ui:** retirer le badge Principal du filtre organismes ([fe19b97](https://github.com/RNF-SI/Cicada/commit/fe19b97a8839763f0d0fc9e6af97023569661f70))
* URL demande d'accès plan de gestion ([4b1f92c](https://github.com/RNF-SI/Cicada/commit/4b1f92c5720fe5e6d556926b671d1534006aa89f))
* variables d'environnement Docker pour démarrage sans .env ([8abd501](https://github.com/RNF-SI/Cicada/commit/8abd501cbdec9cfda12da1ccf389d061e83f7818))
