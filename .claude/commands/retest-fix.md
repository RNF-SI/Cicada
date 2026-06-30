---
description: Reprend une issue après un retour de test KO, en partant du dernier commentaire
argument-hint: <numéro d'issue>
allowed-tools: Bash(gh:*), Bash(git:*), Bash(docker compose exec:*), Edit, Read, Write
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
2. Si le nouveau symptôme n'est pas reproductible ou la description est trop floue,
   NE corrige pas au hasard : commente une demande de précision/étapes et ARRÊTE.
3. Sinon, corrige le symptôme décrit, sur `develop` (déjà à jour).
4. Écris ou complète un test qui couvre CE cas précis (celui qui a régressé) —
   c'est ce qui évite un 3e aller-retour.
5. Lance uniquement les tests concernés (jest --findRelatedTests / pytest ciblé).
6. Commit atomique : `fix(<scope>): <le nouveau symptôme> (#$ARGUMENTS)`.
7. Commente le résumé sur l'issue, garde le label `à tester`. Ne ferme pas.
7bis. Si un point du commentaire dépasse le périmètre de l'issue (demande
      nouvelle, sans rapport avec le bug d'origine), NE le code pas ici :
      signale-le et propose d'ouvrir une issue dédiée.
8. Récap : ce qui était KO, ce qui a été changé, test ajouté.
