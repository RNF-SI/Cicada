---
description: Traite une issue GitHub de bout en bout (classe, corrige, teste, commente)
argument-hint: <numéro d'issue>
allowed-tools: Bash(gh:*), Bash(git:*), Bash(docker compose exec:*), Edit, Read, Write, AskUserQuestion
---

Issue à traiter : #$ARGUMENTS

Contexte préchargé :
!`gh issue view $ARGUMENTS --json title,body,labels,comments`

Procédure :

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

2. Si C → NE corrige PAS tout de suite. POSE-MOI d'abord tes questions
   directement dans le terminal (outil AskUserQuestion) au lieu de trancher seul
   ou de commenter l'issue sans me consulter.
   - Si mes réponses lèvent l'ambiguïté → reclasse l'issue en A/B et reprends à
     l'étape 3.
   - Si l'ambiguïté persiste (vraie décision produit, hors de ta portée) → alors
     SEULEMENT commente tes questions précises sur l'issue
     (`gh issue comment $ARGUMENTS --body "..."`), pose le label `needs: discussion`
     (`gh issue edit $ARGUMENTS --add-label "needs: discussion"`), puis ARRÊTE.

3. Sinon, travaille directement sur `develop`. Assure-toi d'être à jour
   avant de commencer : `git checkout develop && git pull`.

4. Si la correction n'est pas triviale, expose d'abord un plan court
   (fichiers visés + approche) avant de coder. Respecte les conventions
   du CLAUDE.md (architecture, i18n, design system).

5. Applique la correction.

6. Tests, en ne lançant QUE le périmètre concerné :
   - Frontend : `docker compose exec frontend npx jest --findRelatedTests <fichiers modifiés>`
     (si A et frontend → écris/maj le test d'abord)
   - Backend : `docker compose exec web pytest <chemin ou -k mot-clé> -q`
     (si A et backend → écris/maj le test d'abord)
   - Si B → pas de test auto ; ajoute dans TESTS.md :
     `- [ ] #$ARGUMENTS — <titre> — étapes de validation manuelle`

7. Commit atomique au format conventional commits :
   `fix(<scope>): <résumé> (#$ARGUMENTS)`  — un seul commit pour cette issue.

8. OBLIGATOIRE — ne conclus JAMAIS sans ces deux actions, et vérifie qu'elles
   ont bien réussi avant de passer à l'étape 9 :
   a. Commente le résumé de la correction sur l'issue :
      `gh issue comment $ARGUMENTS --body "..."`
   b. Pose le label `à tester` :
      `gh issue edit $ARGUMENTS --add-label "à tester"`
   Si l'une des deux commandes échoue, corrige et relance — ne termine pas tant
   qu'elles n'ont pas abouti.

9. Ne FERME JAMAIS l'issue — c'est moi qui valide et ferme.

10. Termine par un récap compact : bac (A/B/C), fichiers touchés,
    test auto oui/non, étapes manuelles s'il y en a, et confirme explicitement
    que le commentaire de l'étape 8 a bien été posté (l'omettre = travail non fini).
