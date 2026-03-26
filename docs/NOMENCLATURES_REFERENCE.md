# Référentiel des Nomenclatures CICADA

> **Objectif** : Ce document liste toutes les nomenclatures (données de référence) utilisées par l'application CICADA.
> Merci de relire et signaler toute erreur, valeur manquante ou libellé à corriger.
>
> **Source** : Fichiers SQL `backend/nomenclatures_data/types_inserts.sql` et `nomenclatures_inserts.sql`
>
> **Import** : Ces données sont importées automatiquement au démarrage de l'application via `python manage.py import_nomenclatures`.

---

## Sommaire

| # | Type (id) | Mnémonique | Nb valeurs | Origine |
|---|-----------|------------|------------|---------|
| 1 | Espace naturel (1) | `Espace naturel` | 8 | ODASE + CICADA |
| 2 | Évaluation PG (2) | `Evaluation PG` | 3 | ODASE |
| 3 | Rédacteur type (3) | `Rédacteur type` | 3 | ODASE + CICADA |
| 4 | Réalisation DAT (4) | `Réalisation DAT` | 4 | ODASE |
| 5 | Type acte (5) | `Type acte` | 7 | ODASE |
| 6 | Type doc PG (6) | `Type doc PG` | 2 | ODASE |
| 7 | Sexe (7) | `Sexe` | 3 | ODASE |
| 8 | Contrat (8) | `Contrat` | 4 | ODASE |
| 9 | Spécifications DUERP (9) | `Spécifications DUERP` | 7 | ODASE |
| 10 | Sources budget (10) | `Sources budget` | 7 | ODASE |
| 11 | Lien EP (11) | `Lien EP` | 1 | ODASE |
| 12 | Règles (12) | `Règles` | 1 | ODASE |
| 13 | Présence (13) | `Présence` | 2 | ODASE |
| 14 | Activités (14) | `Activités` | 36 | ODASE |
| 15 | Accueil public (15) | `Accueil public` | 4 | ODASE |
| 16 | Aménagements adaptés (16) | `Aménagements adaptés` | 7 | ODASE |
| 17 | Documents accueil public (17) | `Documents accueil public` | 2 | ODASE |
| 18 | Infrastructures d'accueil (18) | — | 0 | ODASE |
| 19 | Activités sportives et loisirs (19) | `Activités sportives et de loisirs` | 54 | ODASE |
| 20 | Encadrement activités (20) | `Encadrement des activités` | 2 | ODASE |
| 21 | Types de pâturages (21) | `Types de paturages` | 4 | ODASE |
| 22 | Acteurs pâturage (22) | `Acteurs paturage` | 2 | ODASE |
| 23 | Plan d'adaptation (31) | `Plan d'adaptation` | 0 | ODASE |
| 24 | Diagnostic de vulnérabilité (32) | `Diagnostic de vulnérabilité` | 0 | ODASE |
| 25 | Intégration NaturAdapt (33) | `Intégration PG de la démarche naturadapt` | 0 | ODASE |
| 26 | Catégorie emploi (34) | `CATEGORIE_EMPLOI` | 14 | ODASE |
| 27 | Sources financement hiérarchisées (35) | `SOURCES_FINANCEMENT_HIERARCHISEES` | 29 | ODASE |
| 28 | Milieux incendie (36) | `Milieux incendie` | 6 | ODASE |
| 29 | Type de responsabilité (40) | `TYPE_RESPONSABILITE` | 5 | CICADA |
| 30 | Niveau de responsabilité (41) | `NIVEAU_RESPONSABILITE` | 4 | CICADA |
| 31 | Catégorie d'enjeu (42) | `CATEGORIE_ENJEU` | 2 | CICADA |
| 32 | Importance de l'enjeu (43) | `IMPORTANCE_ENJEU` | 3 | CICADA |
| 33 | Catégorie de FCR (44) | `CATEGORIE_FCR` | 4 | CICADA |
| 34 | Type d'indicateur (46) | `TYPE_INDICATEUR` | 3 | CICADA |
| 35 | Type de métrique (48) | `TYPE_METRIQUE` | 3 | CICADA |
| 36 | Priorité d'opération (50) | `PRIORITE_OPERATION` | 3 | CICADA |
| 37 | Type d'action (51) | `TYPE_ACTION` | 318 | CICADA (Eden 62) |
| 38 | Type d'opérateur (52) | `OPERATEUR_TYPE` | 4 | CICADA |
| 39 | Catégorie de financement (53) | `CATEGORIE_FINANCE` | 7 | CICADA |
| 40 | Type de document plan (55) | `Type document plan` | 3 | CICADA |
| 41 | Type de suivi (56) | `TYPE_SUIVI` | 3 | CICADA |
| 42 | Statut de suivi (57) | `STATUT_SUIVI` | 3 | CICADA |
| 43 | Objectif de suivi (58) | `OBJECTIF_SUIVI` | 4 | CICADA |
| 44 | Cible de suivi (59) | `CIBLE_SUIVI` | 5 | CICADA |

**Total : 44 types, ~280 valeurs**

---

## Détail par type

### 1. Espace naturel (id_type=1)

Type de site / espace naturel protégé.

| ID | Mnémonique | Libellé | Origine |
|----|------------|---------|---------|
| 42 | `RNN` | Réserve Naturelle Nationale | ODASE |
| 43 | `RNR` | Réserve Naturelle Régionale | ODASE |
| 44 | `RNC` | Réserve Naturelle de Corse | ODASE |
| 93 | `PPRN` | Périmètre de protection de réserve naturelle | ODASE |
| 600 | `PNR` | Parc Naturel Régional | CICADA |
| 601 | `ENS` | Espace Naturel Sensible | CICADA |
| 602 | `APB` | Arrêté de Protection de Biotope | CICADA |
| 604 | `AUTRE` | Autre | CICADA |

### 2. Évaluation PG (id_type=2)

Niveau d'évaluation des plans de gestion.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 45 | `Aucune` | Aucune évaluation |
| 47 | `Intermédiaire` | Évaluation intermédiaire |
| 46 | `Finale` | Évaluation finale |

### 3. Rédacteur type (id_type=3)

Type de rédacteur d'un plan de gestion.

| ID | Mnémonique | Libellé | Origine |
|----|------------|---------|---------|
| 48 | `OG` | Organisme Gestionnaire | ODASE |
| 603 | `BE` | Bureau d'études | CICADA |
| 50 | `Autre` | Autre | ODASE |

### 4. Réalisation DAT (id_type=4)

Niveau de réalisation d'un diagnostic d'ancrage territorial.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 51 | `Oui` | Oui |
| 52 | `Projet planifié` | En projet et planifié sur le plan de gestion |
| 53 | `Projet non planifié` | En projet mais non planifié sur le plan de gestion |
| 54 | `Non` | Non |

### 5. Type acte (id_type=5)

Type de document juridique.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 55 | `PG` | Plan de gestion |
| 56 | `PG simplifié` | Plan de gestion simplifié |
| 57 | `Annexes` | Annexes |
| 58 | `Eval` | Évaluation |
| 59 | `Atlas carto` | Atlas cartographique |
| 60 | `Fiches actions` | Fiches Actions |
| 61 | `Autre` | Autre document |

### 6. Type doc PG (id_type=6)

Type de document de plan de gestion (actes juridiques).

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 64 | `abrogation` | Acte d'abrogation d'espace protégé |
| 66 | `convention gestion` | Convention de gestion |

### 7. Sexe (id_type=7)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 67 | `Homme` | Homme |
| 68 | `Femme` | Femme |
| 74 | `Autre` | Autre |

### 8. Contrat (id_type=8)

Type de contrat de travail.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 69 | `CDD` | Contrat à durée déterminée |
| 70 | `CDI` | Contrat à durée indéterminée |
| 381 | `CDI de projet` | Contrat à durée indéterminée de projet |
| 73 | `Service civique` | Service civique |

### 9. Spécifications DUERP (id_type=9)

Spécifications travail en réserve du DUERP.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 75 | `police` | Mission Police |
| 76 | `montagne` | Milieu Montagne |
| 77 | `marin` | Milieu Marin |
| 78 | `terrain` | Mission terrain |
| 79 | `risque naturel` | Risque Naturel |
| 80 | `risque technologique` | Risque technologique |
| 508 | `zoonose` | Zoonose |

### 10. Sources budget (id_type=10)

Sources de financement du budget de l'organisme gestionnaire.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 382 | `Fonds Propres` | Fonds Propres |
| 81 | `europe` | Fonds européens (FEDER, FEADER, LIFE, INTERREG..) |
| 82 | `France Relance` | Plan France Relance |
| 84 | `Régions` | Régions |
| 87 | `Départements` | Départements |
| 88 | `Caisse des dépôts et consignations` | Caisse des dépôts et consignations |
| 92 | `Dons` | Dons |

### 11. Lien EP (id_type=11)

Type de lien entre espaces protégés.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 94 | `Périmètre de protection` | Périmètre de protection |

### 12. Règles (id_type=12)

Règles d'activités.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 95 | `Autorisé` | Autorisé dans les conditions du droit commun |

### 13. Présence (id_type=13)

Présence de l'activité.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 99 | `Présente` | Activité présente |
| 100 | `Absente` | Activité absente |

### 14. Activités (id_type=14)

Liste des activités (36 valeurs). Voir le fichier SQL pour le détail complet.

| ID | Mnémonique | Libellé | Hiérarchie |
|----|------------|---------|------------|
| 101 | `Circulation` | Circulation des personnes | 1 |
| 102 | `Activités agricoles` | Activités agricoles | 2 |
| 103 | `Maraîchage` | Maraîchage | 2.1 |
| 104 | `Cultures pérennes` | Cultures pérennes : viticulture, arboriculture, oléiculture | 2.2 |
| 105 | `Cultures céréalières…` | Cultures céréalières ou oléoprotéagineuses | 2.3 |
| 106 | `Fauche prairies semi-nat.` | Fauche de prairies semi-naturelles | 2.4 |
| 107 | `Fauche prairies cultivées` | Fauche de prairies cultivées | 2.5 |
| 108 | `Pâturage` | Pâturage | 2.6 |
| 110 | `Apiculture` | Apiculture | 2.7 |
| 111 | `Activités forestières` | Activités forestières | 3 |
| 112 | `Sylviculture` | Sylviculture | 3.1 |
| 115 | `Activités aquacoles` | Activités aquacoles | 4 |
| 116 | `Pisciculture` | Pisciculture | 4.1 |
| 117 | `Conchyliculture` | Conchyliculture | 4.2 |
| 118 | `Chasse` | Chasse | 5 |
| 119 | `Chasse au gros gibier` | Chasse au gros gibier | 5.1 |
| 120 | `Chasse au petit gibier` | Chasse au petit gibier | 5.2 |
| 122 | `Battues administratives` | Battues administratives | 5.3 |
| 123 | `Pêche` | Pêche | 6 |
| 124 | `Pêche professionnelle` | Pêche professionnelle | 6.1 |
| 125 | `Pêche de loisir` | Pêche de loisir | 6.2 |
| 126 | `Cueillettes` | Cueillettes | 7 |
| 127 | `Cueillette baies/fruits` | Cueillette de baies et fruits sauvages | 7.1 |
| 128 | `Cueillette plantes` | Cueillette de plantes | 7.2 |
| 129 | `Cueillette champignons` | Cueillette de champignons | 7.3 |
| 131 | `Activités sportives` | Activités sportives | 8 |
| 132 | `Sport terrestre non motorisé` | Activités sportives et récréatives terrestres non motorisées | 8.1 |
| 133 | `Sport aquatique non motorisé` | Activités sportives et récréatives aquatiques non motorisées | 8.2 |
| 134 | `Sport aérien non motorisé` | Activités sportives et récréatives aériennes non motorisées | 8.3 |
| 135 | `Sport motorisé` | Activités sportives et récréatives motorisées | 8.4 |
| 137 | `Manifestations` | Manifestations sportives et culturelles | 9 |
| 138 | `Manifestations sportives` | Manifestations sportives | 9.1 |
| 139 | `Manifestations culturelles` | Manifestations culturelles et artistiques | 9.2 |
| 140 | `Camping, Bivouac` | Camping, Bivouac | 10 |
| 141 | `Camping` | Camping | 10.1 |
| 142 | `Bivouac` | Bivouac | 10.2 |

### 15. Accueil public (id_type=15)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 143 | `Oui` | Oui, tout le temps |
| 144 | `Oui, certaines saisons` | Oui, mais à certaines saisons seulement |
| 145 | `Oui, mais encadré` | Oui, mais seulement dans le cadre de sorties encadrées |
| 146 | `Non` | Non |

### 16. Aménagements adaptés (id_type=16)

Aménagements adaptés pour personnes handicapées.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 147 | `Amplificateurs auditifs` | Amplificateurs auditifs |
| 148 | `Fauteuils roulants/joëlettes` | Fauteuils roulants / joëlettes |
| 149 | `Signalétiques adaptées` | Signalétiques adaptées (hauteur des panneaux, etc.) |
| 150 | `Plaques et matériels braille` | Plaques et matériels braille |
| 152 | `Observatoire adapté PMR` | Observatoire adapté pour PMR |
| 153 | `Cheminements PMR` | Cheminements spécialisés pour PMR |
| 154 | `Parking PMR` | Parking PMR |

### 17. Documents accueil public (id_type=17)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 155 | `Etude de fréquentation` | Étude de fréquentation |
| 156 | `Plan de circulation` | Plan de circulation |

### 18. Infrastructures d'accueil (id_type=18)

*Aucune valeur définie.*

### 19. Activités sportives et de loisirs (id_type=19)

Liste détaillée (54 valeurs). Hiérarchie en sous-catégories.

<details>
<summary>Voir les 54 valeurs</summary>

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 169 | `Activités terrestres non motorisées` | Activités sportives et récréatives terrestres non motorisées |
| 170 | `Randonnée pédestre` | Randonnée pédestre |
| 171 | `Trail` | Trail |
| 172 | `Marche nordique` | Marche nordique |
| 174 | `Randonnée équestre` | Randonnée équestre |
| 175 | `Cyclisme` | Cyclisme (dont VTT) sans assistance électrique |
| 176 | `Raquettes à neige` | Raquettes à neige |
| 177 | `Ski de randonnée` | Ski de randonnée |
| 178 | `Escalade, alpinisme` | Escalade, alpinisme |
| 179 | `Spéléologie, canyoning` | Spéléologie, canyoning |
| 180 | `Autres terrestres non motorisées` | Autres activités terrestres non motorisées |
| 181 | `Activités aquatiques non motorisées` | Activités sportives et récréatives aquatiques non motorisées |
| 182 | `Baignade, natation` | Baignade, natation |
| 183 | `Canoë-kayak` | Canoë-kayak |
| 184 | `Rafting` | Rafting |
| 185 | `Aviron, pirogue à rame, barque` | Aviron, pirogue à rame, barque, etc. |
| 186 | `Surf, windsurf, kitesurf` | Surf, windsurf, kitesurf, planche à voile |
| 187 | `Plaisance non motorisée` | Plaisance non motorisée |
| 188 | `Canyoning, coastering` | Canyoning, coastering |
| 189 | `Plongée, apnée, rando subaquatique` | Plongée de loisir, masque et tuba, apnée, randonnée subaquatique |
| 190 | `Autres aquatiques non motorisées` | Autres activités aquatiques non motorisées |
| 191 | `Activités motorisées` | Activités sportives et récréatives motorisées |
| 192 | `Vélo assistance électrique` | Vélo (dont VTT) avec assistance électrique |
| 193 | `Motocross` | Motocross |
| 194 | `Quad` | Quad |
| 195 | `Aviation légère, ULM, paramoteur` | Aviation légère, hélicoptère, ULM, paramoteur |
| 196 | `Usage de drones` | Usage de drones |
| 197 | `Sports motonautiques` | Sports motonautiques (jetski, ski nautique, subwing, etc.) |
| 198 | `Plaisance motorisée` | Plaisance motorisée |
| 199 | `Autres motorisées` | Autres activités motorisées |
| 200 | `Manifestations sportives` | Manifestations sportives |
| 201 | `Trails, courses pédestres` | Trails, courses pédestres |
| 202 | `Courses cyclistes` | Courses cyclistes (dont VTT) |
| 203 | `Courses équestres` | Courses équestres |
| 204 | `Courses ski de randonnée` | Courses de ski de randonnée |
| 205 | `Événements sports nautiques` | Événements liés à des sports nautiques |
| 206 | `Événements vol libre` | Événements liés au vol libre |
| 207 | `Autres manifestations sportives` | Autres manifestations sportives |
| 208 | `Manifestations culturelles` | Manifestations culturelles et artistiques |
| 209 | `Expositions` | Expositions |
| 210 | `Cinéma` | Cinéma |
| 211 | `Résidences d'artistes` | Résidences d'artistes |
| 212 | `Photographie` | Photographie |
| 213 | `Concerts, festivals, musiques` | Concerts, festivals, musiques |
| 214 | `Théâtre, spectacles` | Représentations théâtrales, spectacles |
| 215 | `Chantiers/ateliers artistiques` | Chantiers artistiques, ateliers artistiques |
| 216 | `Visites et randonnées à thème` | Visites et randonnées à thème |
| 217 | `Autres manifestations culturelles` | Autres manifestations culturelles et artistiques |
| 218 | `Activités de bien-être` | Activités de bien-être |
| 219 | `Yoga` | Yoga |
| 220 | `Méditation` | Méditation |
| 221 | `Sophrologie` | Sophrologie |
| 222 | `Bain de forêt` | Bain de forêt |
| 223 | `Parcours sensoriel` | Parcours sensoriel |

</details>

### 20. Encadrement des activités (id_type=20)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 165 | `Encadré par la réserve` | Activité organisée par la réserve |
| 167 | `Pratique libre` | Pratique libre |

### 21. Types de pâturages (id_type=21)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 224 | `Bovins` | Bovins |
| 225 | `Ovins` | Ovins |
| 226 | `Caprins` | Caprins |
| 227 | `Equins` | Equins |

### 22. Acteurs pâturage (id_type=22)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 229 | `Indépendant sous convention` | Pâturage exercé par un éleveur indépendant sous convention |
| 231 | `Pâturage absent` | Pâturage absent |

### 23-25. Types liés au changement climatique (id_type=31, 32, 33)

| Type | Libellé | Valeurs |
|------|---------|---------|
| 31 | Plan d'adaptation aux changements climatiques | *Aucune valeur* |
| 32 | Diagnostic de vulnérabilité aux changements climatiques | *Aucune valeur* |
| 33 | Intégration PG de la démarche NaturAdapt | *Aucune valeur* |

### 26. Catégorie d'emploi (id_type=34)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 461 | `ANIMATEUR_EEDD` | Animateur·rice EEDD |
| 462 | `CHARGE_COMMUNICATION` | Chargé·e de communication |
| 464 | `RESPONSABLE_MAISON_RN` | Responsable de maison de RN |
| 465 | `AGENT_TECHNIQUE` | Agent·e technique |
| 467 | `CHARGE_MISSION_SCIENTIFIQUE` | Chargé·e de mission scientifique |
| 468 | `CONSERVATEUR` | Conservateur·rice |
| 469 | `GARDE` | Garde |
| 470 | `RESPONSABLE_GARDES` | Responsable des gardes |
| 471 | `TECHNICIEN_GESTION` | Technicien·ne de gestion |
| 472 | `DIRECTEUR` | Directeur·rice |
| 473 | `GEOMATICIEN` | Géomaticien·ne |
| 474 | `RESPONSABLE_ADMINISTRATIF_FINANCIER` | Responsable administratif·ve et financier·ère |
| 475 | `ASSISTANT_ADMINISTRATIF_FINANCIER` | Assistant·e administratif·ve et financier·ère |
| 476 | `AUTRE` | Autre |

### 27. Sources de financement hiérarchisées (id_type=35)

<details>
<summary>Voir les 29 valeurs</summary>

| ID | Mnémonique | Libellé | Catégorie |
|----|------------|---------|-----------|
| 477 | `EUROPE` | Europe | Europe |
| 478 | `LIFE` | LIFE | Europe |
| 479 | `FEDER` | FEDER | Europe |
| 480 | `FEADER` | FEADER | Europe |
| 481 | `FEAMPA` | FEAMPA | Europe |
| 482 | `FSE_PLUS` | FSE+ | Europe |
| 483 | `INTERREG` | INTERREG | Europe |
| 484 | `EUROPE_AUTRE` | Autre (Europe) | Europe |
| 485 | `ETAT` | État | État |
| 486 | `DOTATION_RN` | Dotation réserve naturelle (BOP113) | État |
| 487 | `PLAN_FRANCE_RELANCE` | Plan France Relance | État |
| 488 | `FONDS_DEDIES_EDD` | Fonds dédiés EDD | État |
| 489 | `FONDS_VERTS` | Fonds Verts | État |
| 490 | `ETAT_AUTRE` | Autre (État) | État |
| 492 | `OFB` | OFB | Opérateurs État |
| 493 | `ONF` | ONF | Opérateurs État |
| 495 | `CAISSE_DEPOTS` | Caisse des dépôts et consignations | Opérateurs État |
| 496 | `OPERATEURS_AUTRE` | Autre (Opérateurs État) | Opérateurs État |
| 497 | `COLLECTIVITES` | Collectivités territoriales | Collectivités |
| 498 | `REGIONS` | Régions | Collectivités |
| 499 | `DEPARTEMENTS` | Départements | Collectivités |
| 500 | `COMMUNAUTE_COMMUNES` | Communauté de communes | Collectivités |
| 501 | `COMMUNES` | Communes | Collectivités |
| 502 | `FONDS_PRIVES` | Fonds privés | Privé |
| 503 | `MECENAT` | Mécénat | Privé |
| 504 | `DONS` | Dons | Privé |
| 505 | `LEGS` | Legs | Privé |
| 506 | `FONDS_PROPRES` | Fonds propres (association) | Privé |
| 507 | `AUTRE` | Autre | Autre |

</details>

### 28. Milieux incendie (id_type=36)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 509 | `agricole` | Agricole |
| 510 | `forestier` | Forestier |
| 511 | `tourbeux` | Tourbeux |
| 512 | `prairie` | Prairie |
| 513 | `landes_broussaille` | Landes-Broussaille |
| 514 | `autres` | Autres |

---

## Nomenclatures CICADA (ajouts spécifiques au projet)

### 29. Type de responsabilité (id_type=40)

Utilisé pour les responsabilités du site en matière de conservation.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 700 | `FLORISTIQUE` | Floristique |
| 701 | `FAUNISTIQUE` | Faunistique |
| 702 | `HABITAT` | Habitat |
| 703 | `GEOLOGIQUE` | Géologique |
| 704 | `PAYSAGER` | Paysager |

### 30. Niveau de responsabilité (id_type=41)

Échelle géographique de la responsabilité.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 710 | `LOCAL` | Local |
| 711 | `REGIONAL` | Régional |
| 712 | `NATIONAL` | National |
| 713 | `INTERNATIONAL` | International |

### 31. Catégorie d'enjeu (id_type=42)

Distinction entre enjeux de conservation et facteurs clés de réussite.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 720 | `ENJEU` | Enjeu de conservation |
| 721 | `FCR` | Facteur Clé de Réussite |

### 32. Importance de l'enjeu (id_type=43)

Niveau de priorité de l'enjeu.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 730 | `PRIORITE_1` | Priorité 1 |
| 731 | `PRIORITE_2` | Priorité 2 |
| 732 | `PRIORITE_3` | Priorité 3 |

### 33. Catégorie de FCR (id_type=44)

Catégorie du Facteur Clé de Réussite.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 740 | `CONNAISSANCE` | Connaissance |
| 741 | `ANCRAGE` | Ancrage territorial |
| 742 | `FONCTIONNEMENT` | Fonctionnement de l'aire protégée |
| 743 | `AUTRE` | Autre |

### 34. Type d'indicateur (id_type=46)

Modèle Pression-État-Réponse (PER).

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 750 | `ETAT` | État |
| 751 | `PRESSION` | Pression |
| 752 | `REPONSE` | Réponse |

### 35. Type de métrique (id_type=48)

Type de donnée pour les métriques d'indicateurs.

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 760 | `NUMERIQUE` | Numérique |
| 761 | `QUALITATIF` | Qualitatif |
| 762 | `BOOLEEN` | Booléen |

### 36. Priorité d'opération (id_type=50)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 770 | `PRIORITE_1` | Priorité 1 |
| 771 | `PRIORITE_2` | Priorité 2 |
| 772 | `PRIORITE_3` | Priorité 3 |

### 37. Type d'action (id_type=51)

Classification hiérarchique des actions dans le plan de gestion.
Source : Codification unique Eden 62, document de travail, février 2026.

**318 entrées** organisées en 9 familles de codes hiérarchiques.
Le champ `hierarchy` encode la relation parent/enfant (IP1.1 est enfant de IP1).

| Préfixe | Famille | Exemples de codes |
|---------|---------|-------------------|
| `IP` | Gestion du patrimoine naturel | IP1 (Restauration), IP2 (Entretien), IP3 (Niveaux d'eau), IP4 (Non intervention), IP5-IP10 |
| `MS` | Maintenance et support | MS1-MS3 (Outillage), MS5-MS6 (Risques), MS7-MS23 (Admin, foncier, budget) |
| `EI` | Études et investigations | EI1-EI11 (Risques, paysages, facteurs, plan de gestion) |
| `CS` | Connaissance et suivi | CS1-CS15 (Surveillance, inventaires, suivis faune/flore/abiotiques) |
| `CI` | Création et maintenance d'infrastructures | CI1-CI11 (Accueil public, technique, patrimoine) |
| `SP` | Surveillance et police | SP1 (Gardes nature), SP2 (Opérations de police) |
| `PA` | Pédagogie et animation | PA1 (Grand public), PA2 (Public ciblé) |
| `CC` | Communication | CC1 (Supports), CC2 (Autres actions) |
| `PR` | Programmes de recherche | PR1 (Programmes scientifiques) |

**Exemples de hiérarchie :**
- `IP1` → Restauration d'habitats naturels (parent)
  - `IP1.1` → Restauration par débroussaillage
  - `IP1.5` → Restauration par pâturage
    - `IP1.5.1` → Restauration par pâturage annuel
    - `IP1.5.2` → Restauration par pâturage ponctuel

### 38. Type d'opérateur (id_type=52)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 800 | `PRESTATAIRE` | Prestataire |
| 801 | `AGENT_RESERVE` | Agent de la réserve |
| 802 | `BENEVOLE` | Bénévole |
| 803 | `STAGIAIRE` | Stagiaire |

### 39. Catégorie de financement (id_type=53)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 810 | `ETAT` | État |
| 811 | `COMMUNE` | Commune |
| 812 | `DEPARTEMENT` | Département |
| 813 | `REGION` | Région |
| 814 | `EUROPE` | Europe |
| 815 | `PRIVE` | Privé |
| 816 | `TOTAL` | Total |

### 40. Type de document plan (id_type=55)

Cycle de vie du plan de gestion (plan initial → évaluation → plan révisé).

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 820 | `PLAN_INITIAL` | Plan initial |
| 821 | `EVAL_MI_PARCOURS` | Évaluation mi-parcours |
| 822 | `PLAN_REVISE` | Plan révisé |

### 41. Type de suivi (id_type=56)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 830 | `SUIVI` | Suivi |
| 831 | `INVENTAIRE` | Inventaire |
| 832 | `SUIVI_INVENTAIRE` | Suivi et inventaire |

### 42. Statut de suivi (id_type=57)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 833 | `EN_COURS` | En cours |
| 834 | `TERMINE` | Terminé |
| 835 | `A_VENIR` | À venir |

### 43. Objectif de suivi (id_type=58)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 836 | `CONSERVATION` | Conservation |
| 837 | `CONNAISSANCE` | Connaissance |
| 838 | `EVALUATION` | Évaluation |
| 839 | `SURVEILLANCE` | Surveillance |

### 44. Cible de suivi (id_type=59)

| ID | Mnémonique | Libellé |
|----|------------|---------|
| 840 | `FLORE` | Flore |
| 841 | `FAUNE` | Faune |
| 842 | `HABITAT` | Habitat |
| 843 | `PROCESSUS` | Processus écologiques |
| 844 | `PAYSAGE` | Paysage |
