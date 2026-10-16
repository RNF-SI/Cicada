# 4.8. Les actions de gestion

## 4.8.1. La saisie d'une action de gestion

Une action se saisit via son formulaire dédié (bouton « Ajouter une action » ou de modification). Vous y renseignez notamment :

- Le type d'action (obligatoire) choisi dans le référentiel GestRef ; et facultativement la catégorie d'action CT88, si celle-ci est différente de celle du référentiel GestRef ;
- Le code de l'action, calculé automatiquement (ex. CS1) et affiché en direct ; le champ « Numéro fixé » permet d'imposer son numéro ;
- L'intitulé (s'il reste vide, il est rempli automatiquement avec le type d'action GestRef à l'enregistrement), les métriques associées et la priorité ;
- Pour une action d'inventaire ou de suivi : les détails de l'inventaire ou du suivi (objectif, cible, taxons ou habitats rattachés), le protocole et la bancarisation de la donnée ;
- La programmation : sites concernés, années, temps de travail, budget et mois prévus ; opérateurs, partenaires et financeurs ;
- La localisation (emprise spatiale) — une case permet de reprendre l'emprise du ou des sites
- Les indicateurs de réponse : un intitulé (obligatoire), puis soit une métrique simple avec une valeur cible, soit une grille de scoring à 5 niveaux (case « Utiliser une grille de scoring »), construite comme celle des métriques des indicateurs état et pression ([§ 4.7](indicateurs-metriques.md)).

Pour les actions de suivis, il est demandé de préciser si le protocole est standardisé ou non :

- oui : recherchez-le dans le catalogue des protocoles standardisés (Une distinction et les 5 protocoles MhéO), consultez sa fiche, puis précisez si vous le respectez strictement (sinon, pourquoi et avec quelles différences).
- non : décrivez votre protocole (nom, ETP par cycle, description, objectif, période d'échantillonnage).

La fréquence (ex. 2 fois par an), intégrée pour les actions de suivis, peut être appliquée automatiquement aux années et aux mois avec le bouton « Appliquer aux années ».

**Le mode de ventilation du budget** : Il définit le niveau de détail de la programmation :

| Mode de ventilation | Ce que vous saisissez |
|---------------------|-----------------------|
| **Pas de ventilation** | Un budget et un temps de travail globaux par année |
| **Par organisme** | Le budget et le temps réparti entre les organismes gestionnaires |
| **Par type de budget** | Un distinction du budget par type (fonctionnement / investissement) |
| **Par organisme + type de budget** | Les deux combinés |
| **Par type de budget + type de poste** | Fonctionnement / investissement, et temps de travail par poste |
| **Par organisme + type de budget + type de poste** | Le niveau le plus détaillé |

<p style="text-align:center"><em style="color:#025359;font-size:0.78rem">Figure 45 : Modes de ventilation budgétaire</em></p>

Lorsque le mode inclut le type de budget, deux cases s'ajoutent :

- « **Déclinaison par type de coût** » : détaille le budget en coût salarial, coût stage, coût prestataire et autres coûts (décochée, seuls les totaux de fonctionnement et d'investissement sont saisis) ;
- « **Saisie automatique du coût salarial** » (modes « + type de poste ») : calcule le coût salarial à partir des jours saisis et du coût jour des postes ([§ 4.3.1](parametrage.md#431-les-postes-ressources-humaines)).

Le temps de travail distingue le temps agent (gestionnaire) et le temps partenaire / bénévole (valorisé), avec une catégorie de dépense (fonctionnement, investissement, bénévolat partenariat). Une nouvelle action reprend le paramétrage de ventilation de la dernière action saisie dans le plan.

Le formulaire propose deux boutons :

- **Enregistrer le brouillon :** sauvegarde votre saisie sans tout valider et vous laisse sur le formulaire (idéal pour saisir progressivement) ; l'action apparaît alors comme « Brouillon » dans les listes ;
- **Valider** : contrôle que tous les champs requis sont remplis, puis enregistre l'action.

!!! tip "Une action ne correspond à aucun type proposé :"

    Sélectionner un niveau supérieur auquel celle-ci peut se rattacher, à défaut d'être précisé à un niveau fin. Si aucune catégorie (même le niveau le plus large) ne permet d'intégrer votre action, choisissez « autre action de gestion ».

<figure markdown="span">
![Formulaire de saisie d'une action de gestion](../assets/figures/fig46.webp){ loading=lazy }
<figcaption>Figure 46 : Formulaire de saisie d'une action de gestion</figcaption>
</figure>

## 4.8.2. La fiche action

Chaque action peut être visualisée sous le format d'une fiche de consultation qui rassemble toutes ses informations de manière plus visuelle : indicateurs et métriques liés, description, protocole et objectifs, temporalité, acteurs, programmation (budget, détail des coûts, temps de travail, financements), indicateurs de réponse, emprise spatiale et réalisation.

Depuis la fiche, vous pouvez :

- « **Voir dans le plan de gestion** » : ouvrir l'enjeu à l'endroit de l'action ;
- « **Voir le suivi de l'action** » ;
- « **Exporter ou imprimer** » : au format Impression / PDF (en choisissant les sections à inclure) ou Excel ;
- « **Modifier l'action** » (plan en brouillon).

<figure markdown="span">
![Fiche action](../assets/figures/fig47.webp){ loading=lazy }
<figcaption>Figure 47 : Fiche action</figcaption>
</figure>
