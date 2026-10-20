---
description: Traite une issue GitHub de bout en bout (classe, corrige, teste, commente)
argument-hint: <numéro d'issue>
allowed-tools: Bash(gh:*), Bash(git:*), Bash(docker compose exec:*), Bash(scripts/export-openapi.sh:*), Bash(grep:*), Edit, Read, Write, AskUserQuestion
---

Issue à traiter : #$ARGUMENTS

Contexte préchargé :
!`gh issue view $ARGUMENTS --json title,body,labels,comments,createdAt`

Procédure :

0. VÉRIFIE D'ABORD QUE CE N'EST PAS DÉJÀ FAIT — beaucoup d'issues ouvertes le
   sont, souvent par un commit qui ne les cite pas.
   - `git log --all --oneline --grep="#$ARGUMENTS"` ;
   - les commits postérieurs à l'ouverture de l'issue (`createdAt`) sur les
     fichiers probablement concernés.
   Si c'est déjà fait : AUCUN commit. Vérifie le comportement (test existant,
   rendu, appel API), puis passe directement à l'étape 8 avec un commentaire
   « ↳ Déjà fait — commit <sha> » qui dit ce que tu as vérifié et comment.

1. CLASSE l'issue dans un bac :
   - A = comportement avec assertion vérifiable (texte/i18n, classe ou style CSS,
     ordre d'éléments, route, valeur calculée, forme d'une réponse API).
   - B = visuel / perceptuel, à valider à l'œil.
   - C = ambigu, trop large, ou label `needs: discussion`.

1bis. IDENTIFIE le dernier commentaire de retour de test (le plus récent, signé
      par le mainteneur / KO de validation). C'est LUI qui définit le travail à
      faire MAINTENANT. L'historique sert de contexte (ce qui a déjà été tenté),
      pas de cahier des charges. Si le dernier commentaire contredit un ancien
      « ↳ Fait », c'est le dernier qui gagne : la correction précédente est
      incomplète ou a régressé.

2. N'HÉSITE PAS À ME POSER DES QUESTIONS — quel que soit le bac.
   Dès qu'un choix change le résultat, demande-moi directement dans le terminal
   (outil AskUserQuestion) plutôt que de trancher seul : corps vide, deux lectures
   possibles, référence sans lien (« comme sur la vitrine », « comme avant »),
   bug impossible à reproduire, plusieurs corrections possibles aux effets
   visibles différents. Une question coûte moins qu'une correction à refaire.
   Ne me demande PAS ce que le code, l'historique git ou l'issue permettent de
   trouver : cherche d'abord, puis pose une question précise avec ce que tu as
   trouvé.
   - Bac C : ne corrige PAS avant mes réponses.
     - Si mes réponses lèvent l'ambiguïté → reclasse l'issue en A/B et reprends
       à l'étape 3.
     - Si l'ambiguïté persiste (vraie décision produit, hors de ta portée) →
       alors SEULEMENT commente tes questions précises sur l'issue
       (`gh issue comment $ARGUMENTS --body "..."`), pose le label
       `needs: discussion` (`gh issue edit $ARGUMENTS --add-label "needs: discussion"`),
       puis ARRÊTE.

3. Sinon, travaille directement sur `develop`. Assure-toi d'être à jour
   avant de commencer : `git checkout develop && git pull`.

4. Si la correction n'est pas triviale, expose d'abord un plan court
   (fichiers visés + approche) avant de coder. Respecte les conventions
   du CLAUDE.md (architecture, i18n, design system).

5. Bac A : ÉCRIS (ou mets à jour) LE TEST AVANT LA CORRECTION, et LANCE-LE :
   il doit ÉCHOUER pour la bonne raison. Un test jamais vu en échec ne prouve
   pas qu'il détecte le bug. S'il passe déjà, soit le bug est ailleurs, soit
   c'est déjà corrigé (retour à l'étape 0).
   Puis applique la correction.

6. Tests :
   - Frontend : `docker compose exec frontend npx jest --findRelatedTests <fichiers modifiés>`
   - Backend : `docker compose exec web pytest <chemin ou -k mot-clé> -q`
   - Le test de l'étape 5 doit maintenant passer.
   - AUTRES TESTS IMPACTÉS : cherche les tests d'autres fichiers qui utilisent
     la fonction, le composant ou l'endpoint modifié
     (`grep -rl "<nom>" backend/tests frontend/src frontend/e2e`) et lance-les
     aussi. Un test cassé ailleurs se corrige dans le même commit, en disant
     pourquoi son attente a changé.
   - Si B → pas de test auto ; ajoute dans TESTS.md :
     `- [ ] #$ARGUMENTS — <titre> — étapes de validation manuelle`
   - Bug impossible à reproduire : dis-le dans le commentaire de l'étape 8,
     avec ce que la correction couvre et ce qu'il faut relever si le symptôme
     revient.

6bis. JEU D'ESSAI (seed_testdata) — seulement si besoin, mais sans hésiter :
   enrichis le seeder concerné (`backend/apps/core/management/commands/seeders/`)
   quand la correction crée un cas, un rôle ou un état absent du jeu d'essai, ou
   quand la validation manuelle demande des données qui n'existent pas (sinon le
   testeur doit les fabriquer à la main).
   - Seed idempotent (relançable), années ancrées sur l'année courante, noms
     sans années quand ils doivent rester stables.
   - Lance-le : `docker compose exec web python manage.py seed_testdata --only=<seeder>`.
   - Mets à jour la section « Test Data Available » du CLAUDE.md (comptes,
     plans, demandes ajoutés).
   - Cite les données à utiliser dans les étapes « À vérifier » du commentaire.

6ter. DOCUMENTATION — OBLIGATOIRE dès que la correction change ce qu'un lecteur
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

6quater. EXPORTS — OBLIGATOIRE dès que la correction touche une donnée, un
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

7. Commit atomique au format conventional commits :
   `fix(<scope>): <résumé> (#$ARGUMENTS)`  — un seul commit pour cette issue,
   tests, seed, documentation et exports compris.

8. OBLIGATOIRE — ne conclus JAMAIS sans ces deux actions, et vérifie qu'elles
   ont bien réussi avant de passer à l'étape 9 :
   a. Commente le résumé de la correction sur l'issue, avec une section
      « À vérifier » (étapes concrètes, données du jeu d'essai à utiliser) :
      `gh issue comment $ARGUMENTS --body "..."`
   b. Pose le label `à tester` :
      `gh issue edit $ARGUMENTS --add-label "à tester"`
   Si l'une des deux commandes échoue, corrige et relance — ne termine pas tant
   qu'elles n'ont pas abouti.

9. Ne FERME JAMAIS l'issue — c'est moi qui valide et ferme.

10. Termine par un récap compact :
    - bac (A/B/C) et, le cas échéant, « déjà fait » (étape 0) ;
    - fichiers touchés ;
    - test auto oui/non — **vu en échec avant correction : oui/non** ;
    - autres tests impactés : lesquels, et ce qui a changé ;
    - seed modifié : oui/non (quoi) ;
    - documentation mise à jour : quelles pages (notice, API/OpenAPI, docs
      techniques, CLAUDE.md), ou « RAS » avec ce qui a été vérifié ;
    - exports impactés : lesquels et comment ils ont été corrigés / testés, ou
      « RAS » avec ce qui a été vérifié ;
    - questions posées et réponses ;
    - étapes manuelles s'il y en a ;
    - confirme explicitement que le commentaire de l'étape 8 a bien été posté
      (l'omettre = travail non fini).
