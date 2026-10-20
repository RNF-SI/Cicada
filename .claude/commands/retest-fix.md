---
description: Reprend une issue après un retour de test KO, en partant du dernier commentaire
argument-hint: <numéro d'issue>
allowed-tools: Bash(gh:*), Bash(git:*), Bash(docker compose exec:*), Bash(scripts/export-openapi.sh:*), Bash(grep:*), Edit, Read, Write, AskUserQuestion
---

Issue à reprendre : #$ARGUMENTS

Contexte :
!`gh issue view $ARGUMENTS --json title,body,labels,comments`

1. Le DERNIER commentaire de retour est ta LISTE DE TRAVAIL. Décompose-le en
   points distincts (« ce qui ne va pas » + « ce qu'il reste à corriger » sont
   souvent plusieurs items). Liste-les explicitement avant de commencer.
   Pour chaque point, décide : à corriger ici / déjà couvert / hors périmètre
   de cette issue (= nouvelle issue à créer, pas à noyer ici).
   Les anciennes notes « ↳ Fait » disent ce qui a déjà été tenté — ne refais pas
   l'ancien, traite les points encore ouverts.
2. N'HÉSITE PAS À ME POSER DES QUESTIONS. Si le nouveau symptôme n'est pas
   reproductible, si le retour est flou ou se lit de deux façons, demande-moi
   d'abord dans le terminal (AskUserQuestion) plutôt que de corriger au hasard.
   Ne me demande pas ce que le code ou l'historique permettent de trouver.
   - Ma réponse lève le doute → continue.
   - Sinon → commente une demande de précision/étapes sur l'issue et ARRÊTE.
3. Corrige sur `develop` (`git checkout develop && git pull`).
4. Écris ou complète d'ABORD un test qui couvre CE cas précis (celui qui a
   régressé), et LANCE-LE : il doit ÉCHOUER avant ta correction — sinon il ne
   protège pas contre un 3e aller-retour. Puis corrige le symptôme décrit.
5. Tests :
   - ceux du périmètre (jest --findRelatedTests / pytest ciblé) ;
   - AUTRES TESTS IMPACTÉS : cherche les tests d'autres fichiers qui utilisent la
     fonction, le composant ou l'endpoint modifié
     (`grep -rl "<nom>" backend/tests frontend/src frontend/e2e`) et lance-les.
5bis. JEU D'ESSAI — si le testeur n'a pas pu reproduire faute de données, ou si
   le cas KO n'existe pas dans `seed_testdata`, enrichis le seeder concerné
   (idempotent, années ancrées sur l'année courante), lance-le, mets à jour
   « Test Data Available » du CLAUDE.md et cite ces données dans le commentaire.
5ter. DOCUMENTATION — OBLIGATOIRE dès que la correction change ce qu'un lecteur
   de la doc voit ou fait. Demande-toi pour chaque cible si elle décrit encore
   juste le comportement après ta correction ; si non, mets-la à jour dans le
   même commit :
   - Notice utilisateur (`documentation/docs/` : `utilisateur/`, `referent/`,
     `admin-organisme/`, `admin-instance/`) — libellé de bouton ou de menu,
     écran, parcours, règle de droits, statut, message affiché. Cherche les
     pages concernées : `grep -rn "<libellé ou notion>" documentation/docs`.
     Garde la numérotation des sections et des figures ; une figure périmée
     se signale dans le commentaire (« capture X à refaire ») plutôt que de
     rester muette.
   - API (`documentation/docs/api/`) — endpoint, serializer, paramètre ou
     permission modifié → relance `scripts/export-openapi.sh` et committe les
     JSON (`openapi.json` + `openapi/<domaine>.json`) ; adapte la page
     d'usage du domaine si le texte ne colle plus.
   - Docs techniques (`docs/*.md` : `API_PLANS_GUIDE.md`, `RECHERCHE.md`,
     `NOMENCLATURES.md`, `DESIGN_SYSTEM.md`, …) et CLAUDE.md — règle métier,
     endpoint, composant partagé ou convention qui y est décrit.
   - Ajout d'une page → entrée dans `nav:` de `documentation/mkdocs.yml`.
   - Si `documentation/` a bougé, vérifie le build strict (lien ou ancre
     cassé = build de l'image en échec) :
     `docker compose exec docs mkdocs build --strict -d /tmp/site`.
   Rien à changer → dis-le explicitement dans le récap (« doc : RAS, vérifié
   <pages regardées> »), ne saute pas l'étape en silence.

5quater. EXPORTS — OBLIGATOIRE dès que la correction touche une donnée, un
   calcul, un libellé ou une règle que les exports reprennent. Les exports
   recalculent souvent de leur côté : corriger l'écran sans eux crée un écart
   silencieux entre ce que l'utilisateur voit et ce qu'il télécharge.
   - Repère les exports qui lisent ce que tu as modifié (champ, modèle,
     nomenclature, règle de calcul budget/RH, mode de ventilation, statut,
     droit d'accès, ordre ou code d'affichage) :
     `grep -rln "<champ ou fonction>" backend/apps/plans/services_export*.py backend/apps/plans/export_theme.py`
     — arborescence (xlsx + présentation), fiches action (xlsx + Word, plan
     entier et action seule), plan Word, budget / RH prévisionnel et suivi,
     tableau de bord, suivi des actions, actions, grilles d'indicateur.
   - Règle de calcul : la source de vérité est partagée
     (`shared/utils/operation-budget.ts` côté front,
     `services_export_finance.py` côté back) — corrige les deux, ne duplique
     pas le calcul dans un module d'export. Fiche action Excel et Word
     partagent leurs fonctions de données : n'en corrige pas qu'un.
   - Colonnes des classeurs exemples / d'import (`example-arborescence-xlsx`,
     `example-actions-xlsx`, `services_import*.py`) : un export qui change de
     forme doit rester relisible par l'import correspondant.
   - Droits : un changement de périmètre de lecture doit rester cohérent avec
     `_can_export_plan()` / `_get_plan_for_export()`.
   - Tests : lance `docker compose exec web pytest tests -k export -q` (au
     minimum les `test_api_exports*.py` et `test_export_*.py`) ; ajoute ou
     adapte une assertion sur la cellule / le paragraphe concerné quand la
     correction change ce que l'export doit contenir.
   - Cite dans « À vérifier » l'export à télécharger et la cellule ou la
     section à contrôler.
   Aucun export concerné → dis-le dans le récap (« exports : RAS, vérifié
   <modules regardés> »).

6. Commit atomique (tests, seed, documentation et exports compris) :
   `fix(<scope>): <le nouveau symptôme> (#$ARGUMENTS)`.
7. Commente le résumé sur l'issue avec une section « À vérifier » (étapes,
   données du jeu d'essai), et fais repasser le label en `à tester`
   (`gh issue edit $ARGUMENTS --remove-label "à corriger" --add-label "à tester"`).
   Vérifie que les deux commandes ont abouti. Ne ferme pas.
7bis. Si un point du commentaire dépasse le périmètre de l'issue (demande
      nouvelle, sans rapport avec le bug d'origine), NE le code pas ici :
      signale-le et propose d'ouvrir une issue dédiée.
8. Récap : ce qui était KO, ce qui a été changé, test ajouté (vu en échec avant
   correction : oui/non), autres tests impactés, seed modifié (oui/non),
   documentation mise à jour (pages, ou « RAS » + ce qui a été vérifié),
   exports impactés (lesquels, ou « RAS » + ce qui a été vérifié),
   questions posées, et confirmation que le commentaire a été posté.
