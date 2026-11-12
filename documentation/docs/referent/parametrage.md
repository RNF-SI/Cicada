# 4.3. Le paramétrage du plan

## 4.3.1. Les postes (ressources humaines)

La page **Postes / RH / Financeurs** décrit les types de postes qui travaillent sur le plan : leur fonction, le nombre de personnes, leur organisme et le coût jour de chaque personne. Aucune donnée nominative n'est enregistrée (RGPD) : un poste est décrit par sa fonction, pas par la personne qui l'occupe.

Cliquez sur « Ajouter un type de poste » puis :

- Choisissez la fonction (si elle manque, « ajouter une nouvelle fonction » : elle ne sera proposée que dans ce plan). Chaque fonction est associée à une des 5 catégories suivantes : salarié, stagiaire, bénévole, partenaire ou prestataire ;
- Indiquez le nombre de personnes ayant la même fonction ;
- Pour les salariés et stagiaires : l'organisme et le coût jour de chaque personne ;
- Pour les bénévoles : un coût jour de 0 est mis par défaut, mais il est possible de le modifier ;
- Pour un prestataire ou un partenaire : l'organisme en texte libre ;
- Éventuellement, un nom local du poste (ex. « garde du secteur nord »), qui remplace la fonction dans les fiches action, et un commentaire (il est recommandé d'éviter l'utilisation des noms ou prénoms, par soucis de respect du RGPD).

**Ces postes alimentent ensuite le temps de travail des actions et le calcul automatique du coût salarial (jours × coût jour).**

**Financeurs.** Sous les postes, la rubrique « Financeurs » liste les financeurs du plan. Un financeur se définit par :

- un **nom** ;
- une **catégorie** : celle de la liste proposée, ou « Autre catégorie (propre à ce plan)… ». Une catégorie ainsi ajoutée ne l'est que pour ce plan, pas pour les autres.

Même nom et même catégorie désignent un seul financeur ; deux noms différents dans la même catégorie font deux financeurs. Les montants se saisissent, si vous le souhaitez, dans la fiche de chaque action (montant prévu sur l'action, [§ 4.8.1](actions.md#481-la-saisie-dune-action-de-gestion)) et au suivi (montant de l'année, [§ 4.9.2](suivi.md#492-le-suivi-des-actions-de-gestion)). Ils ne sont jamais obligatoires. Supprimer un financeur retire aussi ses montants.

<figure markdown="span">
![Page et fenêtre d'ajout de postes/RH](../assets/figures/fig33.webp){ loading=lazy }
<figcaption>Figure 33 : Page et fenêtre d'ajout de postes/RH</figcaption>
</figure>

## 4.3.2. Importer un plan depuis un fichier Excel

Pour reprendre un plan existant sans tout ressaisir à la main, la page « Paramètres » propose deux imports, l'arborescence et les fiches action. L'import n'est possible que sur un plan en brouillon.

- **Import de l'arborescence (enjeux, facteurs, pressions, objectifs, indicateurs, métriques) :**

1. **Partir d'un modèle** : téléchargez le modèle à remplir et/ou un exemple complet pour vous inspirer.
2. **Remplir le fichier dans Excel** : les onglets sont reliés par des codes (E1, F1…) et des listes déroulantes vous guident. Le paramétrage des métriques suit le même chemin : format, pondération et état de référence dans l'onglet « Metriques », grille de scores dans l'onglet « Grilles » (une ligne par métrique, bloc et palier, de 1 = très mauvais à 5 = très bon), blocs complémentaires dans l'onglet « Blocs ». Un plan exporté puis réimporté garde ainsi ses grilles, y compris celles des indicateurs de réponse ; les mesures saisies, elles, ne sont pas reprises. Les seuils sont contrôlés comme à la saisie (borne supérieure au-dessus de la borne inférieure, paliers jointifs) : une grille qui ne les respecte pas est signalée en avertissement et reprise telle quelle, à vérifier après l'import.
3. **Importer votre fichier** : CICADA vérifie le fichier et affiche soit « Fichier valide » avec le nombre d'éléments qui seront créés, soit la liste des anomalies (onglet, ligne, colonne).

Si le plan contient déjà une arborescence, vous choisissez d'ajouter le contenu du fichier à l'existant ou de remplacer tout le contenu (action irréversible, une confirmation est demandée).

4. **Corriger sans repasser par Excel** : le bouton « Corriger dans un tableau » affiche le contenu du fichier à l'écran, cellules en erreur en rouge. Corrigez-les directement, cliquez sur « Revalider », puis « Importer ».
5. **Import des actions** : même principe, avec le classeur des actions (actions, lignes de budget et de ressources humaines), dans un plan qui a déjà son arborescence et aucune action. Le classeur « Actions (format réimportable) » de la rubrique Exports s'y importe tel quel, y compris sur une autre instance :
    - les indicateurs, organismes, sites et métriques sont retrouvés par leur nom (code INPN pour un site) ;
    - un poste absent du plan est créé avec ses fonctions, et le rapport d'import l'annonce ;
    - les suivis et protocoles des actions CS sont créés ;
    - un organisme introuvable dans l'instance est une erreur ; un organisme qui existe mais ne gère aucun site du plan est signalé en avertissement.
    - le type d'action est écrit avec son code (« CS.8.3 — … »). Un type d'une version antérieure du référentiel (classeur exporté en Eden 62, instance passée à Gestref, par exemple) n'est pas refusé : il est remplacé par son équivalent quand la correspondance est sûre ou probable, modifiable ensuite dans la fiche action ; sinon il est conservé et l'action apparaît dans « Actions à actualiser » ([§ 4.8.3](actions.md#483-les-types-daction-à-actualiser)). Le rapport d'import l'annonce pour chaque ligne.

<figure markdown="span">
![Import de l'arborescence - statut valide](../assets/figures/fig34.webp){ loading=lazy }
<figcaption>Figure 34 : Import de l'arborescence - statut valide</figcaption>
</figure>

<figure markdown="span">
![Import de l'arborescence - correction dans un tableau](../assets/figures/fig35.webp){ loading=lazy }
<figcaption>Figure 35 : Import de l'arborescence - correction dans un tableau</figcaption>
</figure>

!!! tip "Mon plan d'origine est dans un tableau qui ne suit pas le modèle, que faire ?"

    A ce stade il n'est pas possible de permettre un import, à partir d'un modèle différent de celui fourni. Dans cette situation, il est recommandé de passer par la saisie manuelle du plan de gestion.

## 4.3.3. Supprimer une version

La suppression d'une version se fait aussi via la page « Paramètres ». **Cela efface définitivement son contenu** (enjeux, actions, suivis, fichiers) et ses liens ; les versions restantes sont renumérotées. <u>**Cette action est irréversible.**</u>
