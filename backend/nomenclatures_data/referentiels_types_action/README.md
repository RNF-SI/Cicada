# Référentiels des types d'action (#751)

Chaque dossier décrit **une version** du référentiel des types d'action et le
**passage** qui y mène depuis la version précédente. Ces fichiers ne sont **pas**
lus au démarrage : rien ne change sur une instance tant que la commande
`passage_types_action` n'y est pas lancée.

```
<version>/
├── version.json         code, libellé, version de départ (`depuis`), catégories écartées
├── referentiel.csv      code,libelle — niveau 0 (« CS ») = catégorie (titre de groupe), niveaux 1 et 2 = types
└── correspondance.csv   ancien_code,nouveau_code,confiance,options,note
```

- `confiance` : `sure` / `probable` → l'action prend le nouveau type (le
  référent peut le corriger) ; `a_arbitrer` → l'action garde son ancien type
  (cohabitation) et ses référents choisissent. La catégorie d'action réserve
  (CT88) ne fait pas partie du référentiel : un passage n'y touche jamais (#788).
- `options` : équivalents possibles séparés par `|` (le `nouveau_code` en
  premier) quand l'ancienne ligne en a plusieurs ; le référent choisit.
- La version de départ des instances actuelles, `EDEN62`, n'a pas de dossier :
  elle est relevée en base (types actifs) au premier passage.

```bash
python manage.py passage_types_action gestref_v1              # simulation (aucune écriture)
python manage.py passage_types_action gestref_v1 --appliquer  # applique + notifie
python manage.py passage_types_action gestref_v1 --annuler    # restaure la version de départ
```

**Un seul dossier** : celui du dernier passage (#791). Quand une version sort,
son dossier remplace le précédent. Une instance dont la version en service
n'est pas `depuis` passe sans aide : rien n'est posé automatiquement, tout
type absent de la nouvelle version est à actualiser à la main. Seul un passage
vers la version déjà en service est refusé.

Voir `documentation/docs/administration/referentiels.md` (« Types d'action »).
