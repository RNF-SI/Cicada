---
description: Traite une issue GitHub de bout en bout (classe, corrige, teste, commente)
argument-hint: <numéro d'issue>
allowed-tools: Bash(gh:*), Bash(git:*), Bash(docker compose exec:*), Edit, Read, Write
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

2. Si C → NE corrige PAS. Commente tes questions précises sur l'issue
   (`gh issue comment $ARGUMENTS --body "..."`), pose le label `needs: discussion`
   (`gh issue edit $ARGUMENTS --add-label "needs: discussion"`), puis ARRÊTE.

3. Sinon, place-toi sur une branche dédiée depuis `develop` :
   `git checkout develop && git pull && git checkout -b fix/$ARGUMENTS`

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

8. Commente le résumé de la correction sur l'issue (`gh issue comment $ARGUMENTS`)
   et pose le label `à tester` (`gh issue edit $ARGUMENTS --add-label "à tester"`).

9. Ne FERME JAMAIS l'issue — c'est moi qui valide et ferme.

10. Termine par un récap compact : bac (A/B/C), fichiers touchés,
    test auto oui/non, étapes manuelles s'il y en a.
