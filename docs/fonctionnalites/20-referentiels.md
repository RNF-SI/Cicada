# 20. Référentiels versionnés (GestRef, PressRef, TaxRef, HabRef)

Les plans s'appuient sur des référentiels nationaux qui évoluent : types d'action (Eden 62 puis GestRef), pressions (PressRef), taxons (TaxRef), habitats (HabRef). Changer de version ne doit ni casser les plans existants ni décider à la place des gestionnaires.

> Exploitation : [administration › Référentiels](../../documentation/docs/administration/referentiels.md). Usage côté référent : notice, [§ 4.8.3 Les types d'action à actualiser](../../documentation/docs/referent/actions.md#483-les-types-daction-à-actualiser).

## Une version = un dossier

```
backend/nomenclatures_data/referentiels_types_action/<version>/   (types d'action)
backend/nomenclatures_data/referentiels_versions/<ref>/<version>/ (PressRef, TaxRef, HabRef)
    version.json         code, libellé, version de départ (« depuis »)
    referentiel.csv      les codes de la version
    correspondance.csv   ancien code → nouveau code, confiance sûre / probable / à arbitrer
```

Un seul dossier par référentiel est livré : celui du dernier passage (#791). Une instance qui n'est pas à la version de départ passe **sans table** : tout code absent de la nouvelle version devient « à actualiser ».

## Le passage, instance par instance

Rien ne change au démarrage. Le passage se lance par un super admin, depuis la page **Administration › Référentiels** (#777), ou par `manage.py passage_types_action` / `passage_referentiel` :

1. **Simulation** : combien d'objets seront convertis automatiquement, combien seront à choisir.
2. **Application** :
   - correspondance **sûre ou probable** → nouveau code, informatif et modifiable ;
   - **à arbitrer** → l'objet garde son ancien code (cohabitation, #776) et apparaît dans « Actions à actualiser » avec les équivalents proposés ;
   - les anciens types sont **désactivés**, jamais supprimés ;
   - une notification par référent concerné.
3. **Annulation** possible tant qu'aucun passage suivant n'a eu lieu.

Tout est journalisé dans `PassageReferentielObjet` (qui a actualisé quoi, pour l'annulation).

Règles : `apps/plans/referentiel_actions.py` (types d'action) et `apps/plans/referentiels/` (moteur générique, #779).

### Ce qui n'est jamais touché

- La **catégorie d'action réserve** (CT88, 9 domaines) est hors du référentiel versionné (#788).
- Les **types d'action complémentaires** (#792) sont convertis un par un ; à arbitrer, ils sont gardés et signalés dans le formulaire.

## Actions à actualiser

- Bandeau non refermable sur toutes les pages tant qu'une action attend (`GET …/referentiel-actions/a-actualiser/compte/`).
- Page `/actions-a-actualiser` : choisir un type, ou « Accepter toutes les propositions » (équivalent unique seulement).
- Le choix est **permis hors brouillon** : c'est la seule modification d'un plan validé ou archivé (#248).
- Une action qui devient CS sans suivi en reçoit un (existant ou nouveau).

## Import d'un classeur écrit avec une ancienne version

Un classeur d'actions exporté avant le passage s'importe : ses types sont convertis avec la même table (#786, retour 09/11), et les actions à arbitrer entrent dans « Actions à actualiser ».

## Consultation et hub

- Page **Référentiels de données** (`/referentiels`, #778) : version en service et téléchargement CSV.
- Le hub de fédération garde **toutes** les versions et correspondances : une recherche par type d'action retrouve les actions d'une instance restée à une version antérieure (#780).
