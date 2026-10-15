---
description: Traite une issue GitHub de bout en bout (classe, corrige, teste, commente)
argument-hint: <numéro d'issue>
allowed-tools: Bash(gh:*), Bash(git:*), Bash(docker compose exec:*), Edit, Read, Write, AskUserQuestion
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

7. Commit atomique au format conventional commits :
   `fix(<scope>): <résumé> (#$ARGUMENTS)`  — un seul commit pour cette issue,
   tests, seed et documentation compris.

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
    - questions posées et réponses ;
    - étapes manuelles s'il y en a ;
    - confirme explicitement que le commentaire de l'étape 8 a bien été posté
      (l'omettre = travail non fini).
