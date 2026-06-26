---
description: Analyse plusieurs issues et propose des lots par fichiers probablement touchés
argument-hint: <numéros d'issues séparés par espace>
allowed-tools: Bash(gh:*), Read
---

Issues à analyser : $ARGUMENTS

Pour chacune : lis-la (`gh issue view <n>`), puis devine les fichiers impactés
(en t'appuyant sur l'architecture décrite dans CLAUDE.md).

Rends UNIQUEMENT un plan (ne corrige rien) :
- Lots « mêmes fichiers » → à faire en SÉQUENTIEL dans une même session
  (ex : renommages i18n qui touchent le même fichier de traduction).
- Issues indépendantes (fichiers disjoints) → PARALLÉLISABLES en worktrees.
- Issues à isoler (bac C probable, needs: discussion) → à ne pas automatiser.

Format : tableau lot / issues / fichiers estimés / séquentiel-ou-parallèle.
