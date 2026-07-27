---
description: Reprend un lot d'issues après retour de test KO, chacune depuis son dernier commentaire (un commit par issue)
argument-hint: <numéros d'issues du lot, ex: "610 618 619 626 628">
allowed-tools: Bash(gh:*), Bash(git:*), Bash(docker compose exec:*), Edit, Read, Write, AskUserQuestion
---

Lot à reprendre après retour KO : #$ARGUMENTS

Ces issues ont été repassées en « à corriger » par le mainteneur. On les reprend
en SÉQUENTIEL dans une seule session : pour CHAQUE issue, c'est le DERNIER
commentaire (PAS le body) qui définit le travail à faire maintenant. Chaque issue
garde son propre commit et sa propre trace.

Contexte préchargé (dernier commentaire de chaque issue) :
!`for n in $ARGUMENTS; do echo "===== #$n ====="; gh issue view $n --json title,labels,comments --jq '"TITRE: \(.title)\nLABELS: \([.labels[].name]|join(", "))\nDERNIER COMMENTAIRE:\n\(.comments[-1].author.login // "—"): \(.comments[-1].body // "(aucun commentaire)")"'; echo; done`

Procédure :

1. PRÉPARE la session, une seule fois :
   - `git checkout develop && git pull`.
   - Pour chaque issue, télécharge et regarde les captures du dernier commentaire
     (beaucoup de retours sont surtout des images).
   - Identifie les fichiers visés par chaque issue et lis-les MAINTENANT.

2. Pour CHAQUE issue, DÉCOMPOSE son dernier commentaire en points distincts
   (« ce qui ne va pas » + « ce qu'il reste à corriger » = souvent plusieurs items).
   Liste-les explicitement. Pour chaque point, classe : à corriger ici / déjà
   couvert / hors périmètre (= nouvelle issue à ouvrir, pas à noyer ici). Les notes
   « ↳ Fait » disent ce qui a déjà été tenté — ne refais pas l'ancien, traite les
   points encore ouverts.

3. ÉTABLIS l'ordre de traitement à l'intérieur du lot :
   - Range les issues pour que les corrections ne se marchent pas dessus (fichiers
     partagés → séquence, jamais d'entrelacement).
   - Signale les dépendances entre issues du lot (« 626 avant 618 parce que… »).
   - Sors du flux les issues dont le retour est trop flou / non reproductible
     (elles partent à l'étape 5).

4. Pour CHAQUE issue, dans l'ordre, en boucle :
   a. Annonce en une ligne les points retenus (issus de l'étape 2) avant de coder.
   b. Corrige le symptôme décrit. Respecte le CLAUDE.md (architecture, i18n, design
      system : variables SCSS, jamais de hex ; composants Kit UI ; WCAG AA).
   c. Écris ou complète un test qui couvre CE cas précis (celui qui a régressé) —
      c'est ce qui évite un 3e aller-retour.
   d. Lance UNIQUEMENT les tests concernés :
      - Frontend : `docker compose exec frontend npx jest --findRelatedTests <fichiers>`.
      - Backend : `docker compose exec web pytest <chemin ou -k mot-clé> -q`.
   e. Commit ATOMIQUE, un par issue : `fix(<scope>): <le nouveau symptôme> (#<n>)`.
      Ne regroupe JAMAIS plusieurs issues dans un même commit.
   f. OBLIGATOIRE — ne passe PAS à l'issue suivante sans ces deux actions, et
      vérifie qu'elles ont abouti :
      - commente le résumé de la correction sur l'issue :
        `gh issue comment <n> --body "..."` ;
      - fais repasser le label de `à corriger` à `à tester` :
        `gh issue edit <n> --remove-label "à corriger" --add-label "à tester"`.
      Si une commande échoue, corrige et relance avant de continuer.
   g. Ne FERME JAMAIS l'issue — c'est le mainteneur qui valide et ferme.
   h. Pour tout point HORS PÉRIMÈTRE repéré à l'étape 2 : ne le code pas ici.
      Ouvre une issue dédiée (`gh issue create`) et référence-la dans le
      commentaire de l'issue courante.

5. Si le retour d'une issue est trop flou / non reproductible : NE corrige pas au
   hasard. POSE-MOI d'abord la question directement dans le terminal (outil
   AskUserQuestion) au lieu de deviner.
   - Si ma réponse lève le doute → reprends l'issue dans le flux (étape 4).
   - Sinon → commente une demande de précision/étapes sur l'issue, LAISSE le label
     `à corriger` en place, et passe à la suivante.

6. À la fin du lot, lance une passe de tests groupée sur les fichiers touchés
   (un seul `jest --findRelatedTests` / `pytest` sur l'ensemble) pour vérifier
   qu'aucune correction n'en a cassé une autre du même lot.

7. Termine par un RÉCAP du lot sous forme de tableau :
   | Issue | Ce qui était KO | Fichiers | Commit | Test | Commenté (oui/non) | Hors-périmètre → issue |
   La colonne « Commenté » doit être `oui` pour toute issue traitée (étape 4f) :
   une case `non` signale un travail non terminé. Puis liste les questions restées
   en suspens (étape 5) et les issues dérivées créées (étape 4h), et ARRÊTE pour
   que je fasse le point avant la suite.
