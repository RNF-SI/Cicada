---
description: Traite un lot d'issues « mêmes fichiers » en séquentiel dans une seule session (un commit par issue)
argument-hint: <numéros d'issues du lot, ex: "534 540 541">
allowed-tools: Bash(gh:*), Bash(git:*), Bash(docker compose exec:*), Bash(scripts/export-openapi.sh:*), Bash(grep:*), Edit, Read, Write, AskUserQuestion
---

Lot à traiter : #$ARGUMENTS

Ces issues ont été regroupées (via /triage) parce qu'elles touchent les MÊMES
fichiers. On les traite donc en SÉQUENTIEL dans une seule session pour charger le
contexte une fois, mais chaque issue garde son propre commit et sa propre trace.

Contexte préchargé (tout le lot) :
!`for n in $ARGUMENTS; do echo "===== #$n ====="; gh issue view $n --json title,body,labels,comments,createdAt --jq '"TITRE: \(.title)\nOUVERTE LE: \(.createdAt)\nLABELS: \([.labels[].name]|join(", "))\nBODY:\n\(.body)\nCOMMENTAIRES: \(.comments|length)\n" + (.comments as $c | ([$c | to_entries[] | select(.value.body|contains("<!-- cicada:questions -->")) | .key] | last) as $i | if $i == null then "QUESTIONS SUR L ISSUE: aucune" else "QUESTIONS POSÉES ET RÉPONSES:\n" + ($c[$i:] | map("--- \(.author.login) le \(.createdAt) ---\n\(.body)") | join("\n")) end)'; echo; done`

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
     tu as vérifié et comment) et pose `à tester` (étape 4i).

2. CLASSE chaque issue du lot dans un bac (comme /fix-issue) :
   - A = assertion vérifiable (texte/i18n, classe/style, ordre, route, calcul, forme d'API).
   - B = visuel/perceptuel, à valider à l'œil.
   - C = ambigu, trop large, ou label `needs: discussion`.
   Pour chaque issue, prends en compte le DERNIER commentaire de retour de test s'il
   existe : c'est lui qui définit le travail à faire maintenant (l'historique = contexte).

2bis. QUESTIONS DÉJÀ POSÉES SUR LES ISSUES — le contexte préchargé affiche,
   pour chaque issue, le dernier commentaire marqué `<!-- cicada:questions -->`
   (questions Q1, Q2… avec options a/b/c et un défaut ⭐) et tous les
   commentaires qui le suivent (réponses possibles, quel qu'en soit l'auteur).
   Pour chaque issue concernée :
   - relève la réponse à chaque question : lettre, texte libre, « OK défauts »
     (= tous les ⭐), ou réponse en prose qui y correspond ;
   - question sans réponse → choix par défaut ⭐, SAUF label
     `needs: discussion` ou défaut « à préciser » : alors pose-la-moi (3bis) ;
   - réponse ambiguë, contradictoire ou hors des options → pose-la-moi (3bis)
     en citant la réponse ;
   - les réponses priment sur le corps de l'issue et sur le commentaire de
     test quand ils se contredisent sur le même point ; la plus récente prime ;
   - une fois tranchées : `gh issue edit <n> --remove-label "question"`, et
     section « Décisions » (Q1 → b, Q2 → défaut a, …) dans le commentaire de
     l'étape 4i.
   Une issue dont une question bloquante reste ouverte passe en bac C.

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
   f. DOCUMENTATION — OBLIGATOIRE dès que la correction change ce qu'un
      lecteur de la doc voit ou fait. Pour chaque cible, demande-toi si elle
      décrit encore juste le comportement ; si non, mets-la à jour dans le
      commit de l'issue :
      - Notice utilisateur (`documentation/docs/` : `utilisateur/`,
        `referent/`, `admin-organisme/`, `admin-instance/`) — libellé de
        bouton ou de menu, écran, parcours, droits, statut, message.
        `grep -rn "<libellé ou notion>" documentation/docs`. Garde la
        numérotation des sections et figures ; une figure périmée se signale
        dans le commentaire (« capture X à refaire »).
      - API (`documentation/docs/api/`) — endpoint, serializer, paramètre ou
        permission modifié → `scripts/export-openapi.sh` et committe les JSON
        (`openapi.json` + `openapi/<domaine>.json`) ; adapte la page d'usage
        du domaine si besoin.
      - Docs techniques (`docs/*.md`) et CLAUDE.md — règle métier, endpoint,
        composant partagé ou convention qui y est décrit.
      - Nouvelle page → entrée dans `nav:` de `documentation/mkdocs.yml`.
      - Si `documentation/` a bougé : `docker compose exec docs mkdocs build --strict -d /tmp/site`
        (lien ou ancre cassé = build de l'image en échec).
      Rien à changer → note « RAS » et ce que tu as vérifié (récap).
   g. EXPORTS — OBLIGATOIRE dès que la correction touche une donnée, un
      calcul, un libellé ou une règle que les exports reprennent (sinon
      l'écran et le fichier téléchargé divergent en silence) :
      - Repère les exports concernés :
        `grep -rln "<champ ou fonction>" backend/apps/plans/services_export*.py backend/apps/plans/export_theme.py`
        — arborescence (xlsx + présentation), fiches action (xlsx + Word,
        plan entier et action seule), plan Word, budget / RH prévisionnel et
        suivi, tableau de bord, suivi des actions, actions, grilles.
      - Calculs budget/RH : source de vérité partagée
        (`shared/utils/operation-budget.ts` / `services_export_finance.py`),
        corrige les deux sans dupliquer dans un module d'export. Fiche action
        Excel et Word partagent leurs fonctions de données : pas l'un sans
        l'autre.
      - Un export qui change de forme doit rester relisible par l'import
        correspondant (`example-*-xlsx`, `services_import*.py`).
      - Droits : rester cohérent avec `_can_export_plan()` /
        `_get_plan_for_export()`.
      - Tests : `docker compose exec web pytest tests -k export -q` ; ajoute
        ou adapte une assertion sur la cellule / le paragraphe concerné.
      - Cite dans « À vérifier » l'export à télécharger et ce qu'il faut y
        contrôler.
      Aucun export concerné → note « RAS » et ce que tu as vérifié (récap).
   h. Commit ATOMIQUE, un par issue (tests, seed, doc et exports compris) :
      `fix(<scope>): <résumé> (#<n>)`.
      Ne regroupe JAMAIS plusieurs issues dans un même commit.
   i. OBLIGATOIRE — ne passe PAS à l'issue suivante sans ces deux actions, et
      vérifie qu'elles ont abouti :
      - commente le résumé sur l'issue, avec une section « À vérifier » (étapes
        concrètes, données du jeu d'essai) : `gh issue comment <n> --body "..."` ;
      - pose le label `à tester` : `gh issue edit <n> --add-label "à tester"`.
      Si une des deux échoue, corrige et relance avant de continuer.
   j. Ne FERME JAMAIS l'issue — c'est le mainteneur qui valide et ferme.

5. Pour CHAQUE issue bac C : ne corrige pas avant mes réponses. POSE-MOI d'abord tes questions
   directement dans le terminal (outil AskUserQuestion) au lieu de trancher seul
   ou de commenter l'issue sans me consulter.
   - Si mes réponses lèvent l'ambiguïté → reclasse l'issue en A/B et traite-la
     dans le flux (étape 4).
   - Si l'ambiguïté persiste (vraie décision produit, hors de ta portée) → alors
     SEULEMENT commente tes questions précises (`gh issue comment <n> --body-file <fichier>`)
     au FORMAT QUESTIONS ci-dessous, pose les labels `question` et
     `needs: discussion` (`gh issue edit <n> --add-label "question" --add-label "needs: discussion"`),
     et passe à la suivante.

   FORMAT QUESTIONS (lu et rempli dans GitHub par une personne non technique) :
   - 1re ligne `<!-- cicada:questions -->` (marqueur relu par l'étape 2bis),
     puis `## ❓ Questions avant de coder` et le paragraphe « Pour répondre » :
     copier le bloc « Réponse » dans un nouveau commentaire, une lettre ou du
     texte libre par question, question sans réponse = défaut ⭐,
     « OK défauts » accepte tout.
   - Une section `### Qn — <sujet>` par question, en termes d'écran et
     d'usage (pas de nom de modèle ni de fonction), options `**a)**`,
     `**b)**`… et une ligne `⭐ **défaut : x**` (ou `à préciser`).
   - Si une partie du travail ne dépend pas des questions, dis-le en tête.
   - Termine par `### Réponse (à copier)` et un bloc de code
     `Q1 :` / `Q2 :` / … / `Remarques :`.

6. À la fin du lot, lance une passe de tests groupée sur les fichiers communs
   touchés (un seul `jest --findRelatedTests` / `pytest` sur l'ensemble) pour
   vérifier qu'aucune correction n'en a cassé une autre du même lot.
   Si le lot a touché des exports, relance aussi `pytest tests -k export -q` ; si
   `documentation/` a bougé, relance le build strict de la doc.

7. Termine par un RÉCAP du lot sous forme de tableau :
   | Issue | Bac | Fichiers | Commit | Test auto (vu en échec ?) | Autres tests impactés | Seed | Doc | Exports | Commenté (oui/non) | Statut (fait / déjà fait / discussion / manuel) |
   Colonnes « Doc » et « Exports » : pages / exports mis à jour, ou « RAS ».
   La colonne « Commenté » doit être `oui` pour toute issue A/B traitée (étape 4i) :
   une case `non` signale un travail non terminé. Puis liste les points de
   validation manuelle (bac B), les questions posées (bac C), et les décisions
   relues sur les issues (étape 2bis — réponse ou défaut appliqué), et ARRÊTE pour que
   je fasse le point avant le lot suivant.
