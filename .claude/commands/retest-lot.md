---
description: Reprend un lot d'issues après retour de test KO, chacune depuis son dernier commentaire (un commit par issue)
argument-hint: <numéros d'issues du lot, ex: "610 618 619 626 628">
allowed-tools: Bash(gh:*), Bash(git:*), Bash(docker compose exec:*), Bash(scripts/export-openapi.sh:*), Bash(grep:*), Edit, Read, Write, AskUserQuestion
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

3bis. N'HÉSITE PAS À ME POSER DES QUESTIONS. Dès qu'un retour se lit de deux
   façons ou qu'un choix change le résultat visible, demande-moi dans le terminal
   (AskUserQuestion) plutôt que de trancher seul — regroupe les questions du lot
   en un seul appel quand c'est possible. Ne me demande pas ce que le code ou
   l'historique permettent de trouver.

4. Pour CHAQUE issue, dans l'ordre, en boucle :
   a. Annonce en une ligne les points retenus (issus de l'étape 2) avant de coder.
   b. Écris ou complète d'ABORD un test qui couvre CE cas précis (celui qui a
      régressé), et LANCE-LE : il doit ÉCHOUER avant la correction — sinon il ne
      protège pas contre un 3e aller-retour.
   c. Corrige le symptôme décrit. Respecte le CLAUDE.md (architecture, i18n, design
      system : variables SCSS, jamais de hex ; composants Kit UI ; WCAG AA).
   d. Tests :
      - Frontend : `docker compose exec frontend npx jest --findRelatedTests <fichiers>`.
      - Backend : `docker compose exec web pytest <chemin ou -k mot-clé> -q`.
      - AUTRES TESTS IMPACTÉS : cherche les tests d'autres fichiers qui
        utilisent la fonction, le composant ou l'endpoint modifié
        (`grep -rl "<nom>" backend/tests frontend/src frontend/e2e`) et lance-les.
        Un test cassé ailleurs se corrige dans le même commit, en disant pourquoi
        son attente a changé.
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
      `fix(<scope>): <le nouveau symptôme> (#<n>)`.
      Ne regroupe JAMAIS plusieurs issues dans un même commit.
   i. OBLIGATOIRE — ne passe PAS à l'issue suivante sans ces deux actions, et
      vérifie qu'elles ont abouti :
      - commente le résumé de la correction sur l'issue, avec une section
        « À vérifier » (étapes, données du jeu d'essai) :
        `gh issue comment <n> --body "..."` ;
      - fais repasser le label de `à corriger` à `à tester` :
        `gh issue edit <n> --remove-label "à corriger" --add-label "à tester"`.
      Si une commande échoue, corrige et relance avant de continuer.
   j. Ne FERME JAMAIS l'issue — c'est le mainteneur qui valide et ferme.
   k. Pour tout point HORS PÉRIMÈTRE repéré à l'étape 2 : ne le code pas ici.
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
   Si le lot a touché des exports, relance aussi `pytest tests -k export -q` ; si
   `documentation/` a bougé, relance le build strict de la doc.

7. Termine par un RÉCAP du lot sous forme de tableau :
   | Issue | Ce qui était KO | Fichiers | Commit | Test (vu en échec ?) | Autres tests impactés | Seed | Doc | Exports | Commenté (oui/non) | Hors-périmètre → issue |
   Colonnes « Doc » et « Exports » : pages / exports mis à jour, ou « RAS ».
   La colonne « Commenté » doit être `oui` pour toute issue traitée (étape 4i) :
   une case `non` signale un travail non terminé. Puis liste les questions restées
   en suspens (étape 5) et les issues dérivées créées (étape 4k), et ARRÊTE pour
   que je fasse le point avant la suite.
