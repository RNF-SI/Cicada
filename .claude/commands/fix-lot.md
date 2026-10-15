---
description: Traite un lot d'issues « mêmes fichiers » en séquentiel dans une seule session (un commit par issue)
argument-hint: <numéros d'issues du lot, ex: "534 540 541">
allowed-tools: Bash(gh:*), Bash(git:*), Bash(docker compose exec:*), Edit, Read, Write, AskUserQuestion
---

Lot à traiter : #$ARGUMENTS

Ces issues ont été regroupées (via /triage) parce qu'elles touchent les MÊMES
fichiers. On les traite donc en SÉQUENTIEL dans une seule session pour charger le
contexte une fois, mais chaque issue garde son propre commit et sa propre trace.

Contexte préchargé (tout le lot) :
!`for n in $ARGUMENTS; do echo "===== #$n ====="; gh issue view $n --json title,body,labels,comments,createdAt --jq '"TITRE: \(.title)\nOUVERTE LE: \(.createdAt)\nLABELS: \([.labels[].name]|join(", "))\nBODY:\n\(.body)\nCOMMENTAIRES: \(.comments|length)"'; echo; done`

Procédure :

1. PRÉPARE la session, une seule fois :
   - `git checkout develop && git pull` (travaille directement sur `develop`).
   - Ouvre les captures des issues qui n'ont qu'une image (télécharge-les et
     regarde-les) — beaucoup de ces retours n'ont pas de texte.
   - Identifie les fichiers communs du lot et lis-les MAINTENANT (contexte partagé).
   - VÉRIFIE POUR CHAQUE ISSUE QU'ELLE N'EST PAS DÉJÀ FAITE (beaucoup d'issues
     ouvertes le sont, souvent par un commit qui ne les cite pas) :
     `git log --all --oneline --grep="#<n>"` et les commits postérieurs à son
     ouverture sur les fichiers concernés. Une issue déjà faite : AUCUN commit ;
     vérifie le comportement, puis commente « ↳ Déjà fait — commit <sha> » (ce que
     tu as vérifié et comment) et pose `à tester` (étape 4g).

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

3bis. N'HÉSITE PAS À ME POSER DES QUESTIONS — quel que soit le bac. Dès qu'un
   choix change le résultat (corps vide, deux lectures possibles, référence sans
   lien comme « comme sur la vitrine », bug non reproductible, plusieurs
   corrections aux effets visibles différents), demande-moi dans le terminal
   (AskUserQuestion) plutôt que de trancher seul. Regroupe les questions du lot
   en un seul appel quand c'est possible. Ne me demande PAS ce que le code,
   l'historique git ou l'issue permettent de trouver.

4. Pour CHAQUE issue A/B, dans l'ordre, en boucle :
   a. Si non trivial, annonce en une ligne le plan (fichiers + approche) avant de coder.
   b. Bac A : ÉCRIS (ou mets à jour) LE TEST AVANT LA CORRECTION et lance-le : il
      doit ÉCHOUER pour la bonne raison (un test jamais vu en échec ne prouve pas
      qu'il détecte le bug ; s'il passe déjà → bug ailleurs, ou déjà corrigé).
   c. Applique la correction. Respecte le CLAUDE.md (architecture, i18n, design system :
      variables SCSS, jamais de hex ; composants Kit UI ; WCAG AA).
   d. Tests, périmètre concerné :
      - Frontend : `docker compose exec frontend npx jest --findRelatedTests <fichiers>`.
      - Backend : `docker compose exec web pytest <chemin ou -k mot-clé> -q`.
      - Le test de l'étape b doit maintenant passer.
      - AUTRES TESTS IMPACTÉS : cherche les tests d'autres fichiers qui
        utilisent la fonction, le composant ou l'endpoint modifié
        (`grep -rl "<nom>" backend/tests frontend/src frontend/e2e`) et lance-les.
        Un test cassé ailleurs se corrige dans le même commit, en disant pourquoi
        son attente a changé.
      - Si B → pas de test auto ; ajoute dans TESTS.md :
        `- [ ] #<n> — <titre> — étapes de validation manuelle`.
      - Bug non reproductible : dis-le dans le commentaire (ce que la correction
        couvre, ce qu'il faut relever si le symptôme revient).
   e. JEU D'ESSAI — seulement si besoin, mais sans hésiter : si la correction
        crée un cas, un rôle ou un état absent de `seed_testdata`, ou si la
        validation manuelle demande des données qui n'existent pas, enrichis le
        seeder concerné (`backend/apps/core/management/commands/seeders/`,
        idempotent, années ancrées sur l'année courante), lance-le
        (`seed_testdata --only=<seeder>`), mets à jour « Test Data Available »
        du CLAUDE.md, et cite ces données dans le « À vérifier » du commentaire.
   f. Commit ATOMIQUE, un par issue (tests, seed et doc compris) :
      `fix(<scope>): <résumé> (#<n>)`.
      Ne regroupe JAMAIS plusieurs issues dans un même commit.
   g. OBLIGATOIRE — ne passe PAS à l'issue suivante sans ces deux actions, et
      vérifie qu'elles ont abouti :
      - commente le résumé sur l'issue, avec une section « À vérifier » (étapes
        concrètes, données du jeu d'essai) : `gh issue comment <n> --body "..."` ;
      - pose le label `à tester` : `gh issue edit <n> --add-label "à tester"`.
      Si une des deux échoue, corrige et relance avant de continuer.
   h. Ne FERME JAMAIS l'issue — c'est le mainteneur qui valide et ferme.

5. Pour CHAQUE issue bac C : ne corrige pas avant mes réponses. POSE-MOI d'abord tes questions
   directement dans le terminal (outil AskUserQuestion) au lieu de trancher seul
   ou de commenter l'issue sans me consulter.
   - Si mes réponses lèvent l'ambiguïté → reclasse l'issue en A/B et traite-la
     dans le flux (étape 4).
   - Si l'ambiguïté persiste (vraie décision produit, hors de ta portée) → alors
     SEULEMENT commente tes questions précises (`gh issue comment <n>`), pose le
     label `needs: discussion` (`gh issue edit <n> --add-label "needs: discussion"`),
     et passe à la suivante.

6. À la fin du lot, lance une passe de tests groupée sur les fichiers communs
   touchés (un seul `jest --findRelatedTests` / `pytest` sur l'ensemble) pour
   vérifier qu'aucune correction n'en a cassé une autre du même lot.

7. Termine par un RÉCAP du lot sous forme de tableau :
   | Issue | Bac | Fichiers | Commit | Test auto (vu en échec ?) | Autres tests impactés | Seed | Commenté (oui/non) | Statut (fait / déjà fait / discussion / manuel) |
   La colonne « Commenté » doit être `oui` pour toute issue A/B traitée (étape 4g) :
   une case `non` signale un travail non terminé. Puis liste les points de
   validation manuelle (bac B) et les questions posées (bac C), et ARRÊTE pour que
   je fasse le point avant le lot suivant.
