---
description: Reprend une issue après un retour de test KO, en partant du dernier commentaire
argument-hint: <numéro d'issue>
allowed-tools: Bash(gh:*), Bash(git:*), Bash(docker compose exec:*), Edit, Read, Write, AskUserQuestion
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
6. Commit atomique (tests, seed et doc compris) :
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
   questions posées, et confirmation que le commentaire a été posté.
