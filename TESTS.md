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
