# API publique des métadonnées des plans de gestion (#645)

API **ouverte, en lecture seule**, exposant les métadonnées des plans de gestion
d'une instance CICADA. Elle existe pour qu'une application tierce de gestion
documentaire — DOCenCEN, côté CEN — puisse rattacher ses documents aux plans
rédigés dans CICADA, en interrogeant l'API régulièrement pour récupérer ce
qu'elle n'a pas encore.

## Pourquoi sur l'instance et non sur le hub

Le hub d'exploration fédérée (#636) ne stocke que l'index de recherche et la
fiche publique d'un plan : ni rédacteurs, ni dates de validation, ni identifiant
Doc'Gestion. Les servir depuis le hub demanderait d'élargir le contrat de
publication **et** de dépendre du consentement de chaque structure, là où le
besoin — relier une GED aux plans d'une instance donnée — est local par nature.

## Activation

Coupée par défaut. Un super administrateur l'ouvre dans
**`/administration/parametres`** → « API publique des métadonnées des plans »
(`SiteConfiguration.api_publique_plans`). Tant qu'elle est coupée, **toutes** les
requêtes reçoivent un `404`.

Ce n'est pas une variable d'environnement : ouvrir un endpoint sans
authentification est une décision de la structure qui déploie l'instance, qui
doit pouvoir être prise — et reprise — sans redéploiement.

## Identifiant d'un plan

Chaque plan porte un `uuid_plan` tiré à sa création (`PlanGestion.uuid_plan`),
et une référence calculée :

```
cicada:<instance_id>:<uuid>      ex. cicada:cen:9f2c1e0a-3b7d-4e51-8a10-6d2c4b91f0aa
```

Le préfixe `cicada` dit de quel outil vient l'identifiant — une GED agrège
plusieurs sources et doit le reconnaître sans table de correspondance.
L'identité de l'instance suit, parce que deux déploiements sont deux bases
distinctes qui peuvent alimenter la même GED.

**Ni `id_pg` ni `slug` ne conviennent** : `id_pg` est une séquence tirée
localement (deux instances produisent couramment le même numéro) et le `slug`
suit le nom, donc change quand le plan est renommé. L'UUID, lui, ne bouge jamais.

## Endpoints

| Méthode | Chemin | Rôle |
|---|---|---|
| `GET` | `/api/public/plans/` | Liste paginée des plans |
| `GET` | `/api/public/plans/{uuid}/` | Un plan par son identifiant stable |

Toute écriture répond `405`. Aucune authentification n'est attendue ni lue.

### Filtres

| Paramètre | Valeur | Effet |
|---|---|---|
| `modifie_depuis` | `2026-08-24` ou `2026-08-24T09:00:00Z` | Plans modifiés depuis cet instant |
| `statut` | `valide`, `modifie`, `archive` | Restreint au statut |
| `id_inpn` | code INPN d'un site | Plans rattachés à ce site |
| `rang` | entier | Restreint au rang |
| `page`, `page_size` | `page_size` ≤ 200 (défaut 50) | Pagination |

Les résultats sont ordonnés par **date de modification croissante**. C'est
délibéré : un rattrapage `modifie_depuis` parcourt les pages pendant que la base
continue de vivre. En ordre croissant, un plan modifié en cours de parcours part
vers la fin de la liste et sera vu deux fois — ce qu'une reprise par identifiant
absorbe. En ordre décroissant, il remonterait avant le curseur et serait
purement **manqué**.

### Périmètre

Exposés : plans **validés, modifiés et terminés**. Les **brouillons ne le sont
jamais** — ce sont des plans en cours de rédaction, dont le nom et la période
changent encore ; les publier sur une API ouverte reviendrait à diffuser du
travail non abouti. Un `?statut=draft` est refusé par un `400`, et non ignoré en
silence.

**Métadonnées uniquement.** Le contenu des plans (enjeux, objectifs,
indicateurs, actions), le budget, les ressources humaines et le suivi ne passent
jamais par cette API : une GED documente des documents, elle n'a pas besoin de
leur substance, et l'endpoint est ouvert. Le cloisonnement est verrouillé par
`TestPerimetreExpose` (`tests/integration/test_api_public_plans.py`).

### Réponse

```json
{
  "reference": "cicada:cen:9f2c1e0a-3b7d-4e51-8a10-6d2c4b91f0aa",
  "uuid": "9f2c1e0a-3b7d-4e51-8a10-6d2c4b91f0aa",
  "instance_id": "cen",
  "id_pg": 42,
  "slug": "camargue-2020-2030",
  "url": "https://cicada.cen-xxx.fr/plans/camargue-2020-2030",

  "nom": "Camargue 2020-2030",
  "rang": 2, "version": "1",
  "annee_debut": 2020, "annee_fin": 2030,
  "surface": "1200.00", "ct88": false, "risque_incendie": true,
  "type_evaluation": null, "type_redacteur": "Gestionnaire",
  "redacteur_nom": "…", "redacteurs": "…", "relecteurs": "…",
  "autres_contributeurs": null, "commentaire": null,
  "id_docgestion_fcen": "DG-42", "id_cdr": null,

  "statut": "valide", "validation_step": null,
  "is_mi_parcours": false, "en_revision": false, "annees_extension": 0,
  "type_document": "Plan initial",
  "date_avis_csrpn": "2020-03-01", "date_validation_comite": "2020-05-12",
  "date_arrete_pref": null, "numero_arrete_pref": null,
  "plan_parent_uuid": null, "plan_parent_reference": null,

  "sites": [
    {
      "id_inpn": "FR3800001",
      "nom": "Réserve nationale de Camargue",
      "slug": "reserve-nationale-de-camargue",
      "type_site": "RNN",
      "surface": 13117.0,
      "gestionnaire_principal": "SNPN"
    }
  ],
  "gestionnaire_principal": "SNPN",

  "date_creation": "2019-11-04T10:22:31Z",
  "date_modification": "2026-08-20T08:14:02Z"
}
```

`url` vaut `null` si l'instance n'a pas déclaré `CICADA_PUBLIC_URL` : derrière un
reverse proxy, une URL reconstruite depuis l'hôte de la requête serait souvent
l'adresse interne du conteneur, et la GED enregistrerait un lien mort sans que
rien ne le signale.

`id_inpn` est le seul identifiant national d'un site, donc la seule clé de
rapprochement possible pour une application tierce. Il est *nullable* — tous les
sites n'en ont pas — et transmis tel quel, sans repli silencieux.

## Rattrapage incrémental — le schéma d'appel attendu

1. Premier passage : parcourir `/api/public/plans/` page par page, stocker
   chaque plan sous sa `reference`.
2. Passages suivants : conserver la `date_modification` la plus haute reçue, et
   rappeler `?modifie_depuis=<cette date>`.
3. Traiter chaque plan en **upsert** par `reference` — un plan peut revenir deux
   fois, il ne doit jamais être dupliqué.

Un plan qui disparaît de l'API a été supprimé, repassé en brouillon, ou l'API a
été refermée. Ces trois cas se ressemblent vus du dehors : ne pas en déduire une
suppression côté GED.

## Questions ouvertes

- **Authentification** : aucune aujourd'hui, conformément au besoin exprimé
  (#645 — « ces informations ne sont pas sensibles »). Si un jour l'API doit
  porter des données restreintes, elle passera par la même brique que le reste
  (dépend de #514, OAuth2/OIDC).
- **Identité nationale des organismes** : comme pour la fédération (#636), un
  organisme n'a pas d'identifiant stable entre instances. Seul son **nom** est
  transmis, pour affichage.
