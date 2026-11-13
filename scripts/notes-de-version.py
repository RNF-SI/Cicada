#!/usr/bin/env python3
"""Notes de version d'une release GitHub, tirées des messages de commit.

    scripts/notes-de-version.py v0.1.72            # depuis le tag précédent
    scripts/notes-de-version.py v0.1.72 v0.1.69    # depuis un tag donné
    scripts/notes-de-version.py v0.1.73 --a-savoir notes.md > release.md

Les commits suivent la convention `type(portée): sujet (#issue)` (commitlint) :
les `feat` deviennent les nouveautés, les `fix` les corrections, le reste
(dépendances, CI, tests…) est replié dans une section technique. Une section
fixe dit à l'administrateur comment mettre à jour et où trouver quoi faire si
ça se passe mal — la page d'aide de l'instance étant servie par l'application,
elle renvoie au guide sur GitHub.

`--a-savoir FICHIER` ajoute en tête un texte rédigé à la main : problème connu,
changement de comportement, geste attendu de l'administrateur… Relire le
résultat avant `gh release create vX.Y.Z --notes-file release.md`.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

DEPOT = 'https://github.com/RNF-SI/Cicada'
GUIDE = f'{DEPOT}/blob/main/documentation/docs/administration/installation.md'

MOTIF = re.compile(r'^(?P<type>[a-z]+)(?:\((?P<portee>[^)]*)\))?(?P<rupture>!)?:\s*(?P<sujet>.+)$')
TECHNIQUE = {'build': 'dépendances', 'ci': 'intégration continue', 'test': 'tests', 'refactor': 'refonte',
             'perf': 'performances', 'docs': 'documentation', 'chore': 'maintenance', 'style': 'style'}


def git(*args):
    return subprocess.run(['git', *args], capture_output=True, text=True, check=True).stdout


def cle(tag):
    return tuple(int(x) for x in re.findall(r'\d+', tag))


def tag_precedent(tag):
    """Dernière release publiée avant `tag` : un tag sans release (version
    abandonnée, comme 0.1.70 et 0.1.71) n'a été installé nulle part, ses
    changements sont à annoncer avec la version suivante."""
    try:
        sortie = subprocess.run(['gh', 'release', 'list', '--exclude-drafts', '--limit', '100',
                                 '--json', 'tagName', '--jq', '.[].tagName'],
                                capture_output=True, text=True, check=True).stdout
        publiees = [t for t in sortie.split() if t.startswith('v')]
    except (OSError, subprocess.CalledProcessError):
        publiees = []
    if tag != 'HEAD':
        publiees = [t for t in publiees if t != tag and cle(t) < cle(tag)]
    if publiees:
        return max(publiees, key=cle)
    return git('describe', '--tags', '--abbrev=0', '--match', 'v*', f'{tag}^').strip()


def commits(depuis, jusqua):
    sortie = git('log', '--no-merges', '--format=%s', f'{depuis}..{jusqua}')
    return [ligne for ligne in sortie.splitlines() if ligne.strip()]


def classer(sujets):
    nouveautes, corrections, technique, autres = [], [], [], []
    for ligne in sujets:
        m = MOTIF.match(ligne)
        if not m:
            autres.append(ligne)
            continue
        if m['type'] == 'chore' and m['sujet'].startswith('bump version'):
            continue
        texte = m['sujet'] + (f" — *{m['portee']}*" if m['portee'] else '')
        if m['rupture']:
            texte = '⚠ ' + texte
        if m['type'] == 'feat':
            nouveautes.append(texte)
        elif m['type'] == 'fix':
            corrections.append(texte)
        else:
            technique.append(f"{TECHNIQUE.get(m['type'], m['type'])} : {texte}")
    return nouveautes, corrections, technique + autres


def notes(tag, depuis, a_savoir=None):
    nouveautes, corrections, technique = classer(commits(depuis, tag))
    version = tag.lstrip('v')
    morceaux = []
    if a_savoir:
        morceaux += ['## À savoir', '', a_savoir.strip(), '']
    for titre, lignes in (('Nouveautés', nouveautes), ('Corrections', corrections)):
        if lignes:
            morceaux += [f'## {titre}', '', *(f'- {ligne}' for ligne in lignes), '']
    if technique:
        morceaux += ['<details><summary>Technique</summary>', '', *(f'- {ligne}' for ligne in technique),
                     '', '</details>', '']
    morceaux += [
        '## Mettre à jour une instance', '',
        f'*Administration › Mise à jour* (bouton « Mettre à jour »), ou sur le serveur '
        f'`sudo cicada-update install {version}`. Rien d\'autre à lancer : la base est sauvegardée et '
        'vérifiée avant le changement de version, et l\'instance revient d\'elle-même à sa version '
        'précédente si la nouvelle ne démarre pas.', '',
        '- Après coup, sur le serveur : `sudo cicada-update status` (versions, conteneurs, issue de la '
        'mise à jour, sauvegarde prise avant).',
        f'- Si ça s\'est mal passé : [guide d\'administration, § 6 « Une mise à jour s\'est mal passée »]'
        f'({GUIDE}) — que faire selon la situation, revenir en arrière.',
        '',
        f'**Historique complet** : {DEPOT}/compare/{depuis}...{tag}',
    ]
    return '\n'.join(morceaux) + '\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('tag', help='tag de la version, ex. v0.1.73 (ou HEAD avant de taguer)')
    p.add_argument('depuis', nargs='?', help='tag de départ (défaut : le tag précédent)')
    p.add_argument('--a-savoir', type=Path, help='texte rédigé à la main, placé en tête')
    args = p.parse_args(argv)
    depuis = args.depuis or tag_precedent(args.tag)
    a_savoir = args.a_savoir.read_text() if args.a_savoir else None
    sys.stdout.write(notes(args.tag, depuis, a_savoir))
    return 0


if __name__ == '__main__':
    sys.exit(main())
