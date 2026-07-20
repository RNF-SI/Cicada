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
- [ ] #453 — Grille de métrique à paliers dupliqués (retour de test 06/07) :
      dans l'arborescence d'un PG en brouillon, créer une métrique de type
      **Texte** dont deux niveaux portent le même libellé (ex. la grille du
      retour : `Bien / Bien / Cool / Très cool / Très cool`). Ouvrir ensuite la
      saisie de l'indicateur (`/plans/:slug/.../indicateur/.../saisie`) et
      choisir « Bien » dans la liste déroulante. Vérifier que :
      1. les **deux paliers en conflit** (niveaux 1 et 2) sont entourés d'un
         contour pointillé noir — auparavant aucun palier n'était mis en
         évidence et rien n'expliquait pourquoi ;
      2. un bandeau orange sous la grille explique que le résultat ne peut pas
         être calculé automatiquement et renvoie vers « Forcer le résultat
         manuellement » ;
      3. cocher « Forcer le résultat manuellement » permet bien de choisir le
         résultat de l'indicateur, et l'enregistrement le conserve ;
      4. choisir « Cool » (libellé unique) met en évidence le seul palier 3,
         sans bandeau, et le résultat automatique est calculé normalement.
