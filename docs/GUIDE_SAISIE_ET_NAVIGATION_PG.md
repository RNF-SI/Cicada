# Guide détaillé — Saisir et naviguer dans un plan de gestion (CICADA)

**Document complémentaire à la notice utilisateur.** Il décrit pas à pas :

1. le **vocabulaire** et la structure d'un plan de gestion dans CICADA ;
2. la **navigation** entre les pages d'un plan (barre latérale) ;
3. le **cycle de vie** d'un plan en détail (statuts et transitions) ;
4. le **parcours complet de saisie**, écran par écran, du plan vide jusqu'au suivi.

> 📸 **Capture 1 — Vue d'ensemble d'un plan**
> **Écran :** fiche d'un plan ouverte, barre latérale visible à gauche, bandeau de statut en haut.
> **À mettre en évidence :** la barre latérale et le bandeau de statut.

> ℹ️ **Convention :** les libellés entre guillemets (« Valider le plan ») sont les **textes exacts**
> affichés à l'écran. Les encadrés **📸 Capture** indiquent où placer une image. Les encadrés
> **💡 Cas d'usage** posent une situation de reprise d'un plan existant et laissent une zone à
> compléter par votre réseau.

---

## 1. Comprendre la structure d'un plan de gestion

Un plan de gestion s'organise en **arborescence**. Comprendre cette hiérarchie est indispensable
pour saisir dans le bon ordre.

```
Plan de gestion
│
├── Enjeux  (et Facteurs clés de réussite — « FCR »)
│   │
│   ├── ONGLET « Détail enjeu »
│   │   └── Facteur d'influence
│   │       └── Pression
│   │
│   ├── ONGLET « Vision à long terme »
│   │   └── Objectif à long terme (OLT)
│   │       └── Niveau d'exigence (NE)
│   │           └── Indicateur d'état
│   │               └── Métrique  (unité, état de référence, seuils de score)
│   │
│   └── ONGLET « Stratégie opérationnelle »
│       └── Objectif opérationnel (OO)
│           └── Résultat attendu (RA)
│               ├── Indicateur de réponse → Métrique
│               └── Action (opération)  → type, calendrier, budget, RH…
│
└── Suivi (disponible une fois le plan validé)
    ├── Tableau de bord   → résultats des indicateurs, année par année
    ├── Suivi des actions → réalisation des actions, année par année
    └── Bilan de la gestion → synthèses et graphiques
```

| Terme | Définition (telle qu'affichée dans CICADA) |
|-------|--------------------------------------------|
| **Enjeu** | Élément de patrimoine naturel (ou facteur clé de réussite) que le plan vise à préserver. |
| **FCR — Facteur clé de réussite** | Condition transversale nécessaire à la réussite de la gestion. |
| **Facteur d'influence** | Élément ou phénomène (naturel ou anthropique) agissant favorablement ou défavorablement sur l'enjeu. |
| **Pression** | Action ou phénomène concret et observable qui matérialise un facteur défavorable. |
| **Objectif à long terme (OLT)** | État souhaité de l'enjeu à l'issue du plan. |
| **Niveau d'exigence (NE)** | Seuil mesurable précisant à quel point l'OLT doit être atteint. |
| **Indicateur d'état** | Paramètre mesurable renseignant sur l'état de conservation de l'enjeu. |
| **Métrique** | Mesure concrète d'un indicateur (avec unité, état de référence et seuils de score). |
| **Objectif opérationnel (OO)** | Objectif concret à atteindre pour répondre à une pression. |
| **Résultat attendu (RA)** | Résultat précis attendu d'un objectif opérationnel. |
| **Action (opération)** | Intervention de gestion programmée (type, calendrier, budget, partenaires…). |

> 💡 **Cas d'usage — Mon plan d'origine n'utilise pas exactement ce découpage**
> **Situation :** mon ancien plan ne distingue pas « objectif à long terme » et « niveau d'exigence », ou regroupe différemment enjeux et objectifs.
> **Réponse (à compléter) :**
> _…………………………………………………………………………………………………_

---

## 2. Naviguer dans un plan de gestion

Dès que vous ouvrez un plan, une **barre latérale** (intitulée « PLANS DE GESTION ») apparaît à
gauche. Elle est le point d'entrée vers toutes les pages du plan.

> 📸 **Capture 2 — Barre latérale du plan**
> **Écran :** barre latérale dépliée, avec les entrées « Vue d'ensemble », « Détails et saisie », « Suivis », « Tableau d'arborescence ».
> **À mettre en évidence :** les quatre entrées principales et les sous-menus dépliés.

### 2.1 Les quatre entrées de la barre latérale

| Entrée | Ce qu'elle ouvre | Sous-menu |
|--------|------------------|-----------|
| **Vue d'ensemble** | La synthèse du plan (informations, enjeux, objectifs, actions, documents). | Pour les gestionnaires, un chevron déplie l'entrée **« Paramètres »** (gestion avancée des versions). |
| **Détails et saisie** | La page **« Liste enjeux et FCR »** : c'est **ici que se fait la saisie du contenu**. | Liste cliquable des **Enjeux** et des **Facteurs clés de réussite** déjà créés. |
| **Suivis** | Le suivi du plan (disponible une fois le plan validé). | **Bilan**, **Suivi des actions**, **Tableau de bord**. |
| **Tableau d'arborescence** | Une vue cartographiée de tout le plan (enjeux ↔ actions). | — |

### 2.2 Logique de navigation

- Cliquer sur **« Vue d'ensemble »** vous ramène toujours à la fiche de synthèse du plan.
- Dans **« Détails et saisie »**, cliquer sur un enjeu de la liste vous emmène directement sur sa
  fiche détaillée (avec ses trois onglets). C'est le chemin le plus rapide pour reprendre la saisie
  d'un enjeu précis.
- Les pages de **« Suivis »** ne sont **modifiables qu'après validation du plan** (voir § 3 et § 4.8).

> 💡 **Conseil de navigation :** gardez la barre latérale comme fil conducteur. Toute la saisie du
> contenu se fait depuis **« Détails et saisie »** ; tout le suivi annuel se fait depuis **« Suivis »**.

---

## 3. Le cycle de vie d'un plan de gestion

### 3.1 Les statuts

Un plan passe par une série de **statuts**. Le statut détermine **si le plan est modifiable** et
**s'il est actif**.

| Statut | Modifiable ? | Signification |
|--------|:-----------:|---------------|
| **Brouillon** | ✅ Oui | Plan en cours de saisie. **Seul statut où le contenu peut être modifié.** |
| **Validé** | ❌ Non | Plan officiel en vigueur. Le suivi devient possible. |
| **Modifié** | ❌ Non | Plan validé puis modifié au moins une fois au sein du même rang. |
| **Archivé** | ❌ Non | Plan clôturé : consultable mais plus actif, suivi inaccessible. |

À ces statuts s'ajoute, pour certains plans, un **circuit de validation réglementaire** (CSRPN) :

| Statut réglementaire | Signification |
|----------------------|---------------|
| **Envoyé pour avis CSRPN** | Plan transmis au CSRPN pour avis. |
| **Comité consultatif** | Avis CSRPN rendu, en attente de validation par le comité consultatif. |
| **Arrêté préfectoral** | (Réserves naturelles nationales) Validé par le comité, en attente d'arrêté. |

Enfin, trois **attributs** peuvent s'ajouter à un plan **validé** sans changer son statut :

- **Extension de durée** (+1 ou +2 ans) ;
- **En cours de révision** (un nouveau plan se prépare en parallèle) ;
- **Évaluation à mi-parcours** (une version porte cette évaluation, unique par chaîne).

> ⚠️ **Règle d'or :** seul un plan en **« Brouillon »** est modifiable. Dès qu'il est validé, un
> bandeau **« Plan verrouillé en lecture seule »** apparaît : *« Ce plan n'est pas en brouillon.
> Pour le modifier, repassez-le en brouillon depuis le cycle de vie ou créez une nouvelle version. »*

> 📸 **Capture 3 — Bandeau de verrouillage en lecture seule**
> **Écran :** fiche d'un plan validé, avec le bandeau « Plan verrouillé en lecture seule » en haut de page.
> **À mettre en évidence :** le bandeau et le bouton de cycle de vie « Remettre en brouillon ».

### 3.2 Les transitions (qui mène à quoi)

```
        ┌─────────────┐   « Valider le plan »   ┌──────────┐
        │  Brouillon  │ ──────────────────────► │  Validé  │
        └─────────────┘                          └──────────┘
              ▲   ▲    « Remettre en brouillon »      │   │
              │   └──────────────────────────────────┘   │
              │                                            │ « Archiver »
   « Réactiver »                                           ▼
        ┌──────────┐                                  ┌──────────┐
        │  Validé  │ ◄──────────────────────────────  │ Archivé  │
        └──────────┘            « Réactiver »          └──────────┘

   Depuis un plan « Validé », sans changer le statut :
     • « Étendre la durée du plan »  /  « Annuler l'extension »
     • « Marquer en cours de révision »  /  « Annuler la révision »
     • « Lancer l'évaluation mi-parcours »
     • « Créer une nouvelle version »  (crée un brouillon enfant)
```

### 3.3 Les actions de cycle de vie (libellés exacts)

Ces actions sont accessibles depuis la fiche du plan (section **« Cycle de vie »** / barre
d'actions). Elles ne sont visibles que selon le statut courant et vos droits.

| Action (bouton) | Effet |
|-----------------|-------|
| **« Valider le plan »** | Passe le brouillon en « Validé ». *Une fois validé, le plan ne sera modifiable que sous la forme d'une nouvelle version ; le suivi devient disponible.* |
| **« Remettre en brouillon »** | Annule la validation pour pouvoir modifier à nouveau (le suivi redevient inaccessible). Une case de confirmation est demandée. |
| **« Archiver »** | Rend le plan inactif ; il reste consultable, le suivi n'est plus accessible. |
| **« Réactiver »** | Réactive un plan archivé. |
| **« Étendre la durée du plan »** | Prolonge le plan de 1 ou 2 ans (transition avec le plan suivant). Le plan reste éditable sur les années ajoutées. |
| **« Annuler l'extension »** | Retire l'extension ; le plan repasse en « Validé » simple. |
| **« Marquer en cours de révision »** | Signale qu'un plan du rang suivant est en préparation. Le plan reste validé. |
| **« Annuler la révision »** | Retire l'indicateur « en cours de révision ». |
| **« Lancer l'évaluation mi-parcours »** | Crée (ou lie) le brouillon d'une évaluation mi-parcours. Unique par chaîne de versions. |
| **« Créer une nouvelle version »** | Crée un **brouillon enfant** (même rang, version +1) à partir du plan validé. |

> ⚠️ **Qui peut agir sur le cycle de vie ?** Les **référents du plan**, les **administrateurs
> d'organisme** et le **super administrateur**. Les autres utilisateurs consultent sans pouvoir
> changer le statut.

> 📸 **Capture 4 — Actions de cycle de vie**
> **Écran :** section « Cycle de vie » d'un plan validé, avec les boutons disponibles.
> **À mettre en évidence :** les boutons « Remettre en brouillon », « Étendre la durée du plan » et « Archiver ».

### 3.4 La chronologie des versions

La section **« Cycle de vie »** affiche une **chronologie verticale** des versions du plan,
regroupées par **rang** (« Rang précédent », « Rang actuel », « Rang à venir »). Chaque nœud est
cliquable et mène à la version correspondante ; le plan affiché porte le badge **« actuel »**.

> 📸 **Capture 5 — Chronologie des versions**
> **Écran :** chronologie « Cycle de vie » avec plusieurs versions (initial, mi-parcours, révisé).
> **À mettre en évidence :** le nœud « actuel » et le regroupement par rang.

### 3.5 Le circuit réglementaire CSRPN (le cas échéant)

Pour les plans concernés, la validation suit un circuit dédié, étape par étape :

1. **« Envoyer pour avis CSRPN »** → le plan part pour avis ;
2. **« Enregistrer l'avis CSRPN »** (saisie de la date de l'avis) ;
3. **« Valider par le comité consultatif »** (saisie de la date) ;
4. (Réserves naturelles nationales) **« Enregistrer l'arrêté préfectoral »** (date + numéro), puis
   validation définitive.

À tout moment, **« Annuler le workflow CSRPN »** ramène le plan en brouillon.

### 3.6 Supprimer une version (Paramètres du plan)

Depuis **Vue d'ensemble → Paramètres** (réservé aux gestionnaires), la page **« Paramètres du plan
de gestion »** permet de **supprimer la version affichée**. *Cela efface définitivement son contenu
(enjeux, opérations, suivis, fichiers) et ses liens ; les versions restantes sont renumérotées.
Action irréversible.*

---

## 4. Parcours complet de saisie d'un plan de gestion

Cette section décrit, **dans l'ordre**, comment saisir un plan de A à Z. C'est le cœur de ce guide.

> ⚠️ **Pré-requis :** la saisie du contenu n'est possible que lorsque le plan est en **« Brouillon »**.
> Sur un plan validé, repassez-le d'abord en brouillon (§ 3.3).

### Étape 0 — Créer le plan

1. Ouvrez le module **Plans de gestion**, cliquez sur **« Créer un plan de gestion »**.
2. Un menu propose deux options :
   - **« À partir d'une base vierge »** (créer un plan neuf) ;
   - **« Sur la base d'un PG existant »** (dupliquer un plan comme modèle).
3. Pour un plan neuf, vous arrivez sur le formulaire **« Saisie des informations générales »**,
   organisé en sections. *Les champs marqués d'un astérisque (\*) sont obligatoires.*

| Section | Champs principaux |
|---------|-------------------|
| **Informations générales** | « Nom du plan de gestion » \*, « Rang du plan de gestion » \* |
| **Période de gestion** | « Année de début » \*, « Année de fin » \* |
| **Caractéristiques** | « Surface totale concernée » (ha), « Méthode de rédaction CT88 » \* (Oui/Non) |
| **Évaluation et rédaction** | « Date de l'avis du CSRPN », « Type d'organisme rédacteur principal », « Organisme rédacteur principal », « Rédacteurs », « Relecteurs », « Autres Contributeurs » |
| **Sites associés** | « Choix des sites » \* — voir ci-dessous |
| **Référents / Commentaire** | référents du plan, commentaire libre |

4. Dans **« Choix des sites »**, un sélecteur de périmètre permet de filtrer : **« Mes sites »**,
   **« Sites de mon organisme »**, **« Tous les sites »**. Cochez un ou plusieurs sites. Si le site
   n'existe pas encore : *« Si votre site n'est pas dans la liste, vous devez d'abord créer le
   site. »*
5. Cliquez sur le bouton de validation en bas du formulaire. **Le plan est créé en « Brouillon »**
   et vous êtes redirigé vers sa **fiche** (« Vue d'ensemble »).

> 📸 **Capture 6 — Formulaire « Saisie des informations générales »**
> **Écran :** formulaire de création de plan, section « Sites associés » visible avec le sélecteur de périmètre.
> **À mettre en évidence :** le champ « Choix des sites » et le sélecteur Mes sites / Mon organisme / Tous.

> 💡 **Cas d'usage — Mon plan existant est déjà validé / déjà évalué**
> **Situation :** je saisis un plan rédigé il y a des années (déjà validé, voire évalué à mi-parcours). Faut-il le créer en brouillon puis le valider, et comment retracer son historique de versions ?
> **Réponse (à compléter) :**
> _…………………………………………………………………………………………………_

### Étape 1 — Ouvrir la page de saisie

Depuis la fiche du plan, dans la barre latérale, cliquez sur **« Détails et saisie »**. Vous
arrivez sur la page **« Enjeux et facteurs clés de réussite »**. Elle présente deux sections :
**« ENJEUX »** et **« FACTEURS CLÉS DE RÉUSSITE »**, sous forme de cartes dépliables (accordéons).

> 📸 **Capture 7 — Page « Enjeux et facteurs clés de réussite »**
> **Écran :** page de saisie avec les sections ENJEUX et FACTEURS CLÉS DE RÉUSSITE et le bouton d'ajout.
> **À mettre en évidence :** le bouton « Ajouter enjeu/FCR » et une carte d'enjeu.

### Étape 2 — Créer un enjeu (ou un FCR)

1. Cliquez sur **« Ajouter enjeu/FCR »**.
2. Remplissez le formulaire de l'enjeu : intitulé court, intitulé long, catégorie, priorité, et les
   éléments associés (**habitats**, **taxons**, **géologie**…), puis l'état actuel.
3. Enregistrez : l'enjeu apparaît dans la liste. Chaque carte propose **« Voir le détail »**,
   **« Modifier »** et **« Supprimer »**.
4. Cliquez sur **« Voir le détail »** pour ouvrir sa fiche : elle comporte **trois onglets** —
   **« Détail enjeu »**, **« Vision à long terme »**, **« Stratégie opérationnelle »**.

> 💡 **Cas d'usage — L'habitat de mon enjeu n'existe pas dans HabRef**
> **Situation :** au moment de renseigner l'enjeu, l'habitat que je veux associer est introuvable dans le référentiel HabRef.
> **Réponse (à compléter) :**
> _…………………………………………………………………………………………………_

### Étape 3 — Onglet « Détail enjeu » : facteurs d'influence et pressions

1. Restez sur l'onglet **« Détail enjeu »**.
2. Sous la partie « État de l'enjeu », cliquez sur **« Ajouter un facteur d'influence »** : un petit
   formulaire en ligne demande l'intitulé et des détails. Enregistrez.
3. Sous chaque facteur, cliquez sur **« Ajouter une pression »** : intitulé, éventuellement un
   **« Type de pression (PressRef) »** (référentiel optionnel), puis détails. Enregistrez.

> 📸 **Capture 8 — Onglet « Détail enjeu » (facteurs et pressions)**
> **Écran :** onglet « Détail enjeu » d'un enjeu, avec un facteur d'influence déplié et ses pressions.
> **À mettre en évidence :** les boutons « Ajouter un facteur d'influence » et « Ajouter une pression ».

### Étape 4 — Onglet « Vision à long terme » : OLT → NE → Indicateurs → Métriques

C'est la branche d'**évaluation** de l'enjeu. On la saisit du haut vers le bas.

1. Ouvrez l'onglet **« Vision à long terme »**.
2. Cliquez sur **« Ajouter un objectif à long terme »** (intitulé + détails). Enregistrez.
3. Sous l'OLT, cliquez sur **« Ajouter un niveau d'exigence »**. Enregistrez.
4. Sous le niveau d'exigence, cliquez sur **« Ajouter un indicateur »** : intitulé, **type
   d'indicateur** (État / Pression / Réponse), indicateur standardisé ou non, description.
5. Sous l'indicateur, cliquez sur **« Ajouter une métrique »**. Renseignez :
   - l'**intitulé** de la métrique et son **type** ;
   - l'**« Unité »**, la **« Pondération »**, l'**« État de référence »** ;
   - les **« Seuils de scores »** : la grille à 5 niveaux **Très mauvais / Mauvais / Moyen / Bon /
     Très bon** (avec le sens de variation et les bornes). Ce sont ces seuils qui traduiront plus
     tard une mesure en score lors du suivi.

> 📸 **Capture 9 — Onglet « Vision à long terme » (hiérarchie OLT → métrique)**
> **Écran :** onglet « Vision à long terme » avec un OLT déplié jusqu'à une métrique et sa grille de seuils.
> **À mettre en évidence :** l'enchaînement OLT → niveau d'exigence → indicateur → métrique et la grille des seuils de score.

> 💡 **Cas d'usage — Mon plan d'origine indiquait une unité pour la métrique**
> **Situation :** la mesure de mon ancien plan a une unité (nombre, surface, %, indice…). Où la renseigner et comment définir les seuils de score correspondants ?
> **Réponse (à compléter) :**
> _…………………………………………………………………………………………………_

> 💡 **Cas d'usage — Ma mesure n'a pas de seuils chiffrés (qualitative / dire d'expert)**
> **Situation :** l'indicateur est qualitatif et ne se prête pas à une grille de score chiffrée.
> **Réponse (à compléter) :**
> _…………………………………………………………………………………………………_

### Étape 5 — Onglet « Stratégie opérationnelle » : objectifs, résultats et actions

C'est la branche **opérationnelle** de l'enjeu.

1. Ouvrez l'onglet **« Stratégie opérationnelle »**.
2. Cliquez sur **« Ajouter un objectif opérationnel »**. Enregistrez.
3. Sous l'objectif, ajoutez un **résultat attendu**, puis, si besoin, un **indicateur de réponse**
   (avec sa métrique).
4. Pour programmer une intervention, cliquez sur **« Ajouter une action »** : vous ouvrez le
   **formulaire d'action** (voir Étape 5 bis).

### Étape 5 bis — Le formulaire d'une action (opération)

Le formulaire d'action s'ouvre sur sa propre page. Il se compose des blocs suivants :

| Bloc | Contenu |
|------|---------|
| **Type d'action** | À choisir dans le référentiel (CS, IP, PA, SP…) ou en texte libre. |
| *(si type « CS »)* **Détails de l'inventaire ou du suivi** | Objectif principal/secondaire, cible(s), taxons et habitats référés. |
| *(si type « CS »)* **Protocole** | Protocole Campanule éventuel, respect du protocole (Oui/Non). |
| **Code de l'action** | Calculé automatiquement après enregistrement (lecture seule). |
| **Intitulé de l'action** | Optionnel ; rempli automatiquement si laissé vide. |
| **Programmation** | Tableau **par année du plan** : mois programmés, budget, jours de travail. Un assistant « fréquence » aide à répartir une action récurrente. |
| **Sites liés** | Le ou les sites concernés par l'action. |
| **Acteurs** | Opérateur(s), partenaire(s), financeur(s). |
| **Sources de financement** | Tableau libellé / catégorie / montant. |
| **Emprise spatiale** | Tracé géographique de l'action (optionnel). |
| **Indicateurs de réponse** | À ajouter **après un premier enregistrement** de l'action. |
| **Détails** | Commentaires libres. |

Deux boutons distincts en bas du formulaire :

- **« Enregistrer le brouillon »** — *« Sauvegarde l'action en l'état (sans contrôler les champs
  requis). Reste sur le formulaire — l'action apparaîtra comme "Brouillon" dans les listes. »*
  → idéal pour saisir en plusieurs fois.
- **« Valider »** — *« Vérifie que tous les champs requis sont remplis, puis retourne à la liste.
  L'action n'est plus marquée comme brouillon. »*

> 📸 **Capture 10 — Formulaire d'une action**
> **Écran :** formulaire d'action, blocs « Type d'action », « Programmation » et la barre de boutons.
> **À mettre en évidence :** le choix du type d'action, le tableau de programmation et les boutons « Enregistrer le brouillon » / « Valider ».

> 💡 **Cas d'usage — Une action ne correspond à aucun type proposé**
> **Situation :** l'action de mon plan ne se range dans aucun type du référentiel (CS, IP, PA, SP…).
> **Réponse (à compléter) :**
> _…………………………………………………………………………………………………_

### Étape 6 — Joindre les documents

Depuis **« Vue d'ensemble »**, la section **Documents** permet de **joindre** des fichiers
(rapports, cartes), de les **télécharger** et de les **supprimer**.

### Étape 7 — Valider le plan

Quand la saisie est complète, ouvrez **« Vue d'ensemble »** puis la section **« Cycle de vie »** et
cliquez sur **« Valider le plan »** (§ 3.3). Le plan passe en **« Validé »**, devient verrouillé en
lecture seule, et **le suivi devient accessible**.

> ℹ️ Si ce plan en remplace un autre dans la même chaîne, CICADA peut vous proposer d'**archiver le
> plan précédent** (« Archiver le plan précédent ? ») et, le cas échéant, de marquer la validation
> comme **évaluation à mi-parcours**.

### Étape 8 — Saisir le suivi (plan validé)

Le menu **« Suivis »** propose trois pages. Tant que le plan n'est pas validé, un bandeau rappelle :
*« Pas de modification possible tant que votre plan de gestion n'est pas validé. »*

#### 8.a — Tableau de bord (suivi des indicateurs)

1. Ouvrez **« Suivis → Tableau de bord »**. Une grille présente les **indicateurs × années**, avec
   une légende de scores (**Très mauvais → Très bon**, plus **Sans donnée**).
2. **Cliquez sur une cellule** (un indicateur, une année) pour ouvrir la page **« Remplir le suivi
   d'un indicateur »**. Vous y saisissez la valeur de chaque métrique de l'année ; le **score** se
   calcule automatiquement à partir des seuils. Vous pouvez **« Saisir manuellement le résultat »**
   et justifier l'écart, ou ajouter un commentaire.
3. Le bouton **« Global »** (ou « Voir l'évaluation globale ») ouvre la vue de synthèse d'un
   indicateur sur toute la période.

> 📸 **Capture 11 — Tableau de bord (indicateurs × années)**
> **Écran :** grille du tableau de bord avec scores colorés et la légende.
> **À mettre en évidence :** une cellule cliquable et la légende des scores.

> 📸 **Capture 12 — Saisie d'un indicateur pour une année**
> **Écran :** page « Remplir le suivi d'un indicateur », avec les métriques et le score de l'année.
> **À mettre en évidence :** le score calculé et l'option « Saisir manuellement le résultat ».

#### 8.b — Suivi des actions

1. Ouvrez **« Suivis → Suivi des actions »** : grille **actions × années**.
2. **Cliquez sur une cellule** pour ouvrir **« Remplir le suivi d'une action »**, avec les sections
   **Réalisation** (« Niveau de réalisation »), **Détails**, **Emprise spatiale réalisée** et
   **Indicateurs de réponse**. Vous pouvez ajouter des commentaires et des pièces jointes.
3. Un récapitulatif annuel par action est accessible via la page **globale** de l'action.

> 📸 **Capture 13 — Suivi des actions + saisie d'une réalisation**
> **Écran :** grille du suivi des actions, et la page de saisie d'une réalisation annuelle.
> **À mettre en évidence :** une cellule de réalisation et le champ « Niveau de réalisation ».

> 💡 **Cas d'usage — Reprendre un historique de réalisations sur plusieurs années**
> **Situation :** mon plan a déjà plusieurs années de mise en œuvre ; je dois saisir rétroactivement la réalisation, année par année.
> **Réponse (à compléter) :**
> _…………………………………………………………………………………………………_

#### 8.c — Bilan de la gestion

La page **« Bilan de la gestion »** synthétise les résultats avec deux onglets, **« Indicateurs »**
et **« Actions »**, et des exports (**« Exporter en PDF »**, **« Exporter en Word »**).

> 📸 **Capture 14 — Bilan de la gestion**
> **Écran :** page Bilan, onglet « Actions », graphiques de synthèse.
> **À mettre en évidence :** les onglets Indicateurs / Actions et les boutons d'export.

### Étape 9 — Vue d'ensemble cartographiée (facultatif)

À tout moment, **« Tableau d'arborescence »** offre une vue d'ensemble du plan (enjeux ↔ actions),
avec zoom et bascule entre la vue « Enjeux » et la vue « Actions ». Utile pour vérifier la cohérence
globale après la saisie.

---

## 5. Récapitulatif du parcours

| Étape | Page | Action clé |
|-------|------|------------|
| 0 | Créer un plan de gestion | Formulaire « Saisie des informations générales » → plan en **Brouillon** |
| 1 | Détails et saisie | Ouvrir « Enjeux et facteurs clés de réussite » |
| 2 | Détails et saisie | « Ajouter enjeu/FCR » → « Voir le détail » |
| 3 | Onglet « Détail enjeu » | Facteurs d'influence → Pressions |
| 4 | Onglet « Vision à long terme » | OLT → Niveau d'exigence → Indicateur → Métrique (+ seuils) |
| 5 | Onglet « Stratégie opérationnelle » | Objectif opérationnel → Résultat attendu → **Action** |
| 6 | Vue d'ensemble | Joindre les documents |
| 7 | Cycle de vie | « Valider le plan » |
| 8 | Suivis | Tableau de bord, Suivi des actions, Bilan |

> ℹ️ Les encadrés **💡 Cas d'usage** laissés vides dans ce guide sont à compléter par votre réseau,
> à partir des situations concrètes rencontrées lors de la saisie des plans existants.
