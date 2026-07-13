---
description: Traite un lot d'issues « mêmes fichiers » en séquentiel dans une seule session (un commit par issue)
argument-hint: <numéros d'issues du lot, ex: "534 540 541">
allowed-tools: Bash(gh:*), Bash(git:*), Bash(docker compose exec:*), Edit, Read, Write
---

Lot à traiter : #$ARGUMENTS

Ces issues ont été regroupées (via /triage) parce qu'elles touchent les MÊMES
fichiers. On les traite donc en SÉQUENTIEL dans une seule session pour charger le
contexte une fois, mais chaque issue garde son propre commit et sa propre trace.

Contexte préchargé (tout le lot) :
!`for n in $ARGUMENTS; do echo "===== #$n ====="; gh issue view $n --json title,body,labels,comments --jq '"TITRE: \(.title)\nLABELS: \([.labels[].name]|join(", "))\nBODY:\n\(.body)\nCOMMENTAIRES: \(.comments|length)"'; echo; done`

Procédure :

1. PRÉPARE la session, une seule fois :
   - `git checkout develop && git pull` (travaille directement sur `develop`).
   - Ouvre les captures des issues qui n'ont qu'une image (télécharge-les et
     regarde-les) — beaucoup de ces retours n'ont pas de texte.
   - Identifie les fichiers communs du lot et lis-les MAINTENANT (contexte partagé).

2. CLASSE chaque issue du lot dans un bac (comme /fix-issue) :
   - A = assertion vérifiable (texte/i18n, classe/style, ordre, route, calcul, forme d'API).
   - B = visuel/perceptuel, à valider à l'œil.
   - C = ambigu, trop large, ou label `needs: discussion`.
   Pour chaque issue, prends en compte le DERNIER commentaire de retour de test s'il
   existe : c'est lui qui définit le travail à faire maintenant (l'historique = contexte).

3. ÉTABLIS l'ordre de traitement à l'intérieur du lot :
   - Range les issues pour que les corrections ne se marchent pas dessus (ex : une
     refonte structurelle d'un composant AVANT un simple renommage dans ce composant).
   - Signale les dépendances entre issues du lot (« 540 doit passer avant 541 parce que… »).
   - Sors les issues bac C du flux : NE les corrige pas.

4. Pour CHAQUE issue A/B, dans l'ordre, en boucle :
   a. Si non trivial, annonce en une ligne le plan (fichiers + approche) avant de coder.
   b. Applique la correction. Respecte le CLAUDE.md (architecture, i18n, design system :
      variables SCSS, jamais de hex ; composants Kit UI ; WCAG AA).
   c. Tests, périmètre concerné UNIQUEMENT :
      - Frontend : `docker compose exec frontend npx jest --findRelatedTests <fichiers>`
        (si A et frontend → écris/maj le test d'abord).
      - Backend : `docker compose exec web pytest <chemin ou -k mot-clé> -q`
        (si A et backend → écris/maj le test d'abord).
      - Si B → pas de test auto ; ajoute dans TESTS.md :
        `- [ ] #<n> — <titre> — étapes de validation manuelle`.
   d. Commit ATOMIQUE, un par issue : `fix(<scope>): <résumé> (#<n>)`.
      Ne regroupe JAMAIS plusieurs issues dans un même commit.
   e. Commente le résumé sur l'issue (`gh issue comment <n>`) et pose le label
      `à tester` (`gh issue edit <n> --add-label "à tester"`).
   f. Ne FERME JAMAIS l'issue — c'est le mainteneur qui valide et ferme.

5. Pour CHAQUE issue bac C : ne corrige pas. Commente tes questions précises
   (`gh issue comment <n>`), pose le label `needs: discussion`
   (`gh issue edit <n> --add-label "needs: discussion"`), et passe à la suivante.

6. À la fin du lot, lance une passe de tests groupée sur les fichiers communs
   touchés (un seul `jest --findRelatedTests` / `pytest` sur l'ensemble) pour
   vérifier qu'aucune correction n'en a cassé une autre du même lot.

7. Termine par un RÉCAP du lot sous forme de tableau :
   | Issue | Bac | Fichiers | Commit | Test auto | Statut (fait / discussion / manuel) |
   Puis liste les points de validation manuelle (bac B) et les questions posées
   (bac C), et ARRÊTE pour que je fasse le point avant le lot suivant.
