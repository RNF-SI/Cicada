# Versions de PressRef, TaxRef et HabRef (#779)

Même principe que les types d'action (`../referentiels_types_action/`) : un
dossier par version, lu **uniquement** par la commande de passage (ou la page
super-admin « Référentiels »), jamais au démarrage.

```
<pressref|taxref|habref>/<version>/
├── version.json         {"code": "TAXREF_V19", "libelle": "TaxRef v19", "depuis": "TAXREF_V18"}
├── referentiel.csv      code,libelle — obligatoire pour PressRef (nomenclature), facultatif sinon
└── correspondance.csv   ancien_code,nouveau_code,confiance,options,note
```

- **Un seul dossier par référentiel** : celui du dernier passage (#791) ; une
  nouvelle version remplace le dossier précédent. Une instance dont la version
  en service n'est pas `depuis` passe sans aide (codes cités par la table, ou
  absents de la nouvelle version pour PressRef : à actualiser, sans proposition).
- Ne lister dans `correspondance.csv` que les codes qui changent : un code
  absent de la table et présent dans la nouvelle version n'est pas touché.
- `confiance` : `sure` / `probable` → code posé (modifiable par les référents) ;
  `a_arbitrer` → l'ancien code reste (cohabitation) jusqu'au choix du référent
  parmi `options` (codes séparés par `|`) ou ailleurs dans le référentiel.
- TaxRef / HabRef : importer d'abord la nouvelle version (`import_taxref
  --version …`, `import_habref`) ; le passage remappe ensuite les codes portés
  par les enjeux, les responsabilités de site et les suivis. Sans
  `referentiel.csv`, les codes de la table sont vérifiés dans la base importée.
- Versions de départ, relevées en base au premier passage : `PRESSREF_CARET_V1`,
  `TAXREF_V<version importée>`, `HABREF_V<version importée>`.

```bash
python manage.py passage_referentiel taxref taxref_v19              # simulation
python manage.py passage_referentiel taxref taxref_v19 --appliquer  # applique + notifie
python manage.py passage_referentiel taxref taxref_v19 --annuler
```
