# Validations manuelles en attente

> Les points de validation en attente sont aussi suivis dans Obsidian
> (notes de recette), qui servent de support aux séances avec Sophie.

## Lot suivi des actions / arborescence (retours 16/07/2026)

- [ ] #567 — Arborescence : une action créée **directement dans un indicateur**
      (sans métrique) apparaît sous cet indicateur, en vue normale ET inversée.
- [ ] #568 — Pagination : plan avec > 20 actions → une pagination apparaît en bas
      des trois onglets (Réalisation, Budget, RH) et permet d'aller page 2, 3…
      Vérifier que les sous-totaux d'organisme (Budget/RH) restent le total complet.
- [ ] #569 — RH : saisir de la RH (jours) dans une fiche action, puis vérifier que
      le total remonte dans l'onglet RH de synthèse (Année en cours / Période
      écoulée / Total), y compris le réalisé.
- [ ] #570 — Sélecteur d'année : dans Budget/RH, cliquer sur l'année de l'en-tête
      « Année en cours », choisir une autre année → « Période écoulée » se réajuste
      aux années antérieures.
- [ ] #566 — Tags priorité : les priorités 1/2/3 s'affichent en tag kit UI
      (rouge/orange/jaune) dans le tableau de suivi, la liste des enjeux et la
      fiche action (couleur + libellé lisibles, texte noir).

## Lot indicateurs / fiche action (retours 16/07/2026 — #571-575)

- [ ] #571 — Fiche action : « Objectif principal » et « Cible principale »
      affichent un libellé lisible (ex. « Composante abiotique »), plus le code.
- [ ] #572 — Indicateur global : la carte « Moyenne » porte une icône cohérente
      avec le nombre (2,1/5 → mauvais) ; « État courant » reste la dernière année.
- [ ] #573 — Métrique multibloc : le tableau récap des seuils affiche TOUS les
      blocs (intitulé + intervalle, reliés par ET/OU) et pas seulement le bloc 1.
      (Décision : logique de combinaison ET/OU conservée, seul l'affichage change.)
- [ ] #574 — Créer un nouvel indicateur SOUS UN RÉSULTAT ATTENDU avec une
      métrique directement : la métrique est bien enregistrée (ou un message
      d'erreur explicite s'affiche en cas d'échec, plus de disparition silencieuse).
- [ ] #575 — Seuils de métrique : saisir 3-4 décimales (ex. 4,111) → s'affiche
      entièrement après enregistrement ; une saisie à 5+ décimales s'enregistre
      (arrondie à 4).
- [ ] #577 — Design page paramètres du plan de gestion : ouvrir
      `/plans/:slug/parametres` (menu « Paramètres » de la sidebar, brouillon).
      Vérifier : le contenu occupe plus de largeur (≈1100px, plus les 760px),
      chaque section est une carte blanche arrondie avec bordure (danger-zone =
      bordure gauche rouge) ; les sections d'import affichent un bouton « Choisir
      un fichier… » (outline kit UI, icône dossier) + le nom du fichier
      sélectionné (au lieu de l'input natif) ; marges/paddings homogènes.
- [ ] #582 — Légende « année » du suivi (marqueur trait au lieu d'un rond) :
      ouvrir la saisie d'un suivi/inventaire (`/plans/:slug/.../suivi/.../saisie`).
      Sous la barre des années, vérifier que la légende affiche désormais des
      **traits** et non des ronds : « Année prévue (action programmée) » = trait
      plein bleu-vert (primary), « Année non prévue » = trait pointillé gris,
      chacun aligné visuellement sur le soulignement des onglets d'années
      correspondants.
- [ ] #453 — Paliers homonymes reliés chacun à leur case de grille :
      dans l'arborescence d'un PG en brouillon, créer une métrique de type
      **Texte** dont deux niveaux portent le même libellé (grille du retour de
      test : `Bien / Bien / Cool / Très cool / Très cool`). Ouvrir la saisie de
      l'indicateur (`/plans/:slug/.../indicateur/.../saisie`) et vérifier que :
      1. la liste déroulante affiche « Bien (niveau 1) » et « Bien (niveau 2) »,
         mais « Cool » **sans** suffixe (seuls les doublons sont désambiguïsés) ;
      2. choisir « Bien (niveau 1) » met en évidence la **1re** case de la
         grille, et « Bien (niveau 2) » la **2e** — c'était le symptôme du
         retour de test : aucune case ne s'allumait ;
      3. enregistrer, quitter la page, revenir : le niveau choisi est bien
         restauré (et pas retombé sur le premier homonyme) ;
      4. idem sur une métrique de type **Chiffre** avec deux paliers de même
         valeur ;
      5. une grille sans doublon est inchangée (pas de suffixe, score auto
         calculé normalement) ;
      6. **reprise de l'existant** : sur une mesure enregistrée AVANT cette
         version avec un libellé dupliqué, le premier palier homonyme est
         présélectionné, les paliers concernés sont entourés en pointillés et un
         bandeau invite à confirmer le niveau ; après enregistrement, le bandeau
         disparaît définitivement.

- [ ] #591 — Tableau d'arborescence : affichage à revoir — validation visuelle
      1. ouvrir un plan → **Tableau d'arborescence** ;
      2. vérifier qu'il n'y a **plus de légende** en haut ;
      3. vérifier la palette par colonne : enjeu bleu-vert (texte blanc), état
         actuel / facteur / pression vert pâle, OLT et niveau d'exigence saumon,
         OO et résultat attendu jaune, indicateurs et métriques dans la teinte
         claire de leur branche, action terra cotta (texte blanc) ;
      4. vérifier que la case **« État actuel » occupe deux colonnes**, si bien
         que les OLT s'alignent sur les OO et que les deux branches d'un enjeu se
         terminent sur la même colonne « Action » ;
      5. vérifier les libellés : « Action » (et non « Opération »),
         « Indicateur d'état » sur la branche haute, « Indicateur de réponse »
         sur la branche basse ;
      6. basculer sur la vue **Actions → Enjeux** : mêmes couleurs et libellés ;
      7. déplier / replier et zoomer sur une case : la largeur des colonnes se
         recalcule correctement malgré la case à double largeur.

- [ ] #585 — Icônes copier / lier sur les actions — validation visuelle
      1. sur un plan **en brouillon**, ouvrir un enjeu → onglet OLT puis onglet
         Opérations ;
      2. vérifier la présence des icônes 🔗 et ⧉ sur l'entête de chaque action,
         avant le crayon et la corbeille ;
      3. « lier » : la cible « Directement sur l'indicateur » est **grisée**
         (infobulle explicative), seules les métriques sont sélectionnables ;
      4. après avoir lié une action à une seconde métrique, vérifier le badge
         « Liée à plusieurs métriques » sur sa carte ;
      5. « copier » : la cible « Directement sur l'indicateur » est cette fois
         sélectionnable ; vérifier que la copie est bien indépendante
         (renommer la copie ne renomme pas l'originale) ;
      6. sur un plan **validé**, vérifier que les deux icônes n'apparaissent pas.

- [ ] #586 — Drag and drop d'une action entre indicateurs — validation visuelle
      1. sur un plan en brouillon, glisser une action d'un indicateur d'état
         vers un autre indicateur d'état ;
      2. glisser une action d'un indicateur d'état vers un indicateur de
         **réponse** (et l'inverse) ;
      3. déposer sur un indicateur **sans aucune action** : la zone en pointillés
         « Glisser une action ici » doit apparaître et accepter le dépôt ;
      4. glisser une action **rattachée à une métrique** : une confirmation
         nommant les métriques perdues doit s'afficher ; refuser → rien ne bouge,
         accepter → l'action est déplacée et le bandeau de métriques nettoyé ;
      5. vérifier que le code d'action (CS1, IP2…) se met à jour après le
         déplacement, sans rechargement complet de la page ;
      6. réordonner une action **dans** son propre indicateur : comportement
         inchangé.

- [ ] #625 — Alignement du tableau du suivi budgétaire — validation visuelle
      1. ouvrir la saisie du suivi d'une action d'un plan **validé** dont le
         budget est ventilé par organisme (`/plans/<slug>/suivis/saisie/<id>/<année>`) ;
      2. carte « Programmation et budget » : le tableau ne doit **plus dépasser**
         le bord droit de la carte blanche — s'il est plus large que la carte, il
         défile horizontalement à l'intérieur de celle-ci ;
      3. vérifier sur une fenêtre étroite (~1400 px) et sur un plan de 10 ans ou
         plus (le plus grand nombre de colonnes années) ;
      4. fonds de lignes : chaque ligne « (prévi.) » est grise, chaque ligne
         « (réalisé) » est blanche — y compris **après** les lignes d'en-tête
         (nom d'organisme, « Fonctionnement » / « Investissement », « TOTAL ») ;
         un même libellé ne doit plus changer de fond d'un bloc à l'autre ;
      5. la colonne de l'année active reste surlignée terra-cotta sur toutes les
         lignes, prévisionnelles comprises.
- [ ] #624 — Ventilation « par type de budget + type de poste » — sur une action en mode « Par type de budget + type de poste » : le tableau budget affiche Fonctionnement (coût salarial calculé, stage, prestataire, autres coûts, commentaire, total) puis Investissement (salarial, prestataire, autres, commentaire, total) puis le budget total, SANS bloc par organisme. Vérifier que « Dupliquer valeurs de la 1ère colonne » recopie le détail, puis, dans le suivi de l'année, que les mêmes lignes apparaissent en prévu / réalisé. Sur une action déjà enregistrée dans ce mode AVANT la correction, vérifier que les montants Fonctionnement/Investissement se retrouvent en « Autres coûts ».
- [ ] #621 — Zones « Glisser … ici » — dans l'arborescence d'un plan en brouillon : plus aucun cadre pointillé « Glisser une action ici » / « Glisser un indicateur ici » / « Glisser une pression ici » à l'écran au repos. Vérifier ensuite que le glisser-déposer fonctionne toujours **vers un conteneur vide** : le cadre pointillé doit réapparaître dès qu'on commence à faire glisser un élément, et le dépôt aboutir (indicateur vers un NE/RA sans indicateur, action vers un indicateur sans action, pression vers un facteur sans pression).
- [ ] #613 — Fiche action : budget annuel et détail des coûts — sur une action ventilée « par organisme + type de budget + type de poste » (ou « par type de budget + type de poste »), ouvrir la fiche de l'action : les colonnes Fonctionnement / Investissement / Budget de la section PROGRAMMATION doivent afficher les montants réels (et non 0 €), cohérents avec le total de la section « Répartition par organisme gestionnaire ». Vérifier le nouveau tableau « Détail des coûts » (coût salarial calculé, stage, prestataire, autres coûts, en fonctionnement et investissement) et que le temps bénévole/partenaire est compté en jours mais pas en euros.
- [ ] #629 — Export des cartes : fond de carte — depuis un plan, lancer l'export « Fiches action » (xlsx) sur une action dont l'emprise (ou le site) a une géométrie. Dans la rubrique « Localisation de l'action », la vignette doit montrer un vrai fond de carte OpenStreetMap (routes, communes, littoral) avec l'emprise en surcouche vert pâle translucide, contour bleu-vert, et la mention « © OpenStreetMap » en bas à droite — plus le « carré vert » plein. Vérifier aussi : le cadrage laisse une marge autour de l'emprise ; l'image ne chevauche pas les lignes suivantes ; sur un serveur sans accès Internet (ou avec `EXPORT_MAP_TILE_URL=` vide dans `.env`), l'export aboutit quand même avec l'ancien rendu (aplat beige + contour).
- [ ] #634 — Exploration après mise à jour — sur une instance dont l'index de recherche date d'une version antérieure : au redémarrage, le log doit afficher « Index absent ou périmé → reconstruction complète (version 2) » puis le détail des plans réindexés. Vérifier ensuite, dans l'exploration **sans toucher au switch « Rechercher dans les titres uniquement »**, qu'un nom d'espèce (français ET latin), un protocole standardisé (« STOC »), un habitat, un élément de géologie ou une référence PressRef remonte bien les enjeux ET les actions concernés. Redémarrer une seconde fois : le log doit dire « Index à jour (version 2), rien à faire » (aucune reconstruction inutile).
- [ ] #634 — Fiche d'un plan sans contenu — ouvrir depuis l'exploration un plan validé qui n'a ni enjeu ni action : sous les compteurs à zéro, un bandeau bleu doit expliquer que le plan n'a pas de contenu structuré (au lieu d'une page blanche).
- [ ] #634 — Rappel du périmètre — le texte « Seuls les plans de gestion validés sont explorables… » doit apparaître sur la page d'accueil de l'exploration (dans les deux modes) et en haut des deux pages de résultats (contenus et plans).
- [ ] #626 — Carte de l'emprise — exporter la fiche d'une action ayant une emprise : la vignette doit s'afficher **dans le cadre à droite du libellé « Emprise de l'action »** (colonne des valeurs), et non en dessous dans la marge des libellés. Vérifier qu'elle ne recouvre pas la section « 3) Détail du volet administratif et financier ».
- [ ] #601 — Couleur des exports par instance — dans Administration > Paramètres, section « Couleur des exports » : choisir une couleur (preset ou personnalisée), enregistrer, puis lancer un export arborescence, une fiche action, un budget et la fiche Word. Les titres, bandeaux et en-têtes doivent porter la couleur choisie ; les couleurs de score de la grille de lecture (rouge → cyan) doivent, elles, rester inchangées. Revenir à #025359 doit tout remettre en bleu-vert CICADA.
